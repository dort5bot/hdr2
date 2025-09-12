import asyncio
import logging
import os
import signal
import sys
from contextlib import AsyncExitStack

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from prometheus_client import start_http_server

from config import (
    TELEGRAM_BOT_TOKEN,
    ADMIN_IDS,
    TEMP_DIR,
    USE_WEBHOOK,
    WEBHOOK_URL,
    WEBHOOK_PATH,
    WEBHOOK_HOST,
    WEBHOOK_PORT,
    PROMETHEUS_PORT,
    LOGS_DIR
)
from utils.handler_loader import setup_handlers
from jobs.scheduled_tasks import scheduler
from utils.metrics import set_active_processes, increment_db_operation

# Logging configuration
LOGS_DIR.mkdir(exist_ok=True, parents=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "bot.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

async def on_startup():
    """Run on bot startup"""
    try:
        # Ensure directories exist
        TEMP_DIR.mkdir(exist_ok=True, parents=True)
        
        logger.info("Starting application initialization...")
        
        # Start Prometheus metrics server
        await start_metrics_server()
        
        # Start scheduler
        asyncio.create_task(scheduler(bot))
        logger.info("Scheduler started")
        
        # Load all handlers automatically
        loaded_count = await setup_handlers(dp, "handlers")
        logger.info(f"{loaded_count} handler(s) loaded successfully")
        
        # Initialize database
        from utils.db_utils import db_manager
        increment_db_operation('startup')
        logger.info("Database initialized")
        
        # Initialize source manager
        from utils.source_utils import source_manager
        await source_manager.load_from_backup()
        logger.info("Source manager initialized")
        
        # Set webhook if using webhook mode
        if USE_WEBHOOK:
            webhook_path = f"{WEBHOOK_PATH}/{TELEGRAM_BOT_TOKEN}"
            await bot.set_webhook(f"{WEBHOOK_URL}{webhook_path}")
            logger.info(f"Webhook set successfully: {WEBHOOK_URL}{webhook_path}")
        
        # Send startup message to admins
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, "✅ HIDIR Botu başlatıldı.\n\nSistem durumu: /status")
            except Exception as e:
                logger.error(f"Admin mesajı gönderilemedi ({admin_id}): {e}")
        
        set_active_processes(1)
        logger.info("✅ Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

async def on_shutdown():
    """Run on bot shutdown"""
    try:
        logger.info("Shutting down application...")
        set_active_processes(0)
        
        if USE_WEBHOOK:
            await bot.delete_webhook()
            logger.info("Webhook deleted")
        
        await bot.session.close()
        logger.info("Bot session closed")
        
        # Cleanup resources
        from utils.file_utils import cleanup_temp
        await cleanup_temp()
        logger.info("Temporary files cleaned up")
        
        logger.info("✅ Application shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")

async def start_metrics_server():
    """Start Prometheus metrics server"""
    try:
        # Start in background thread
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, start_http_server, PROMETHEUS_PORT)
        logger.info(f"Prometheus metrics server started on port {PROMETHEUS_PORT}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")

async def main_webhook():
    """Webhook mode"""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_path = f"{WEBHOOK_PATH}/{TELEGRAM_BOT_TOKEN}"

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=webhook_path)

    setup_application(app, dp, bot=bot)

    try:
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, host=WEBHOOK_HOST, port=WEBHOOK_PORT)
        await site.start()
        
        logger.info(f"Webhook server started on {WEBHOOK_HOST}:{WEBHOOK_PORT}")
        logger.info(f"Webhook URL: {WEBHOOK_URL}{webhook_path}")
        
        # Handle graceful shutdown
        async with AsyncExitStack() as stack:
            # Wait for shutdown signal
            await asyncio.Event().wait()
            
    except Exception as e:
        logger.error(f"Webhook server error: {e}")
        raise
    finally:
        if 'runner' in locals():
            await runner.cleanup()

async def main_polling():
    """Polling mode"""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        logger.info("Starting in polling mode...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Polling error: {e}")
        raise
    finally:
        await bot.session.close()

async def main():
    """Main function"""
    try:
        if USE_WEBHOOK:
            logger.info("Starting in WEBHOOK mode")
            await main_webhook()
        else:
            logger.info("Starting in POLLING mode")
            await main_polling()
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

def handle_signal(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    asyncio.create_task(on_shutdown())
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application manually stopped")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
