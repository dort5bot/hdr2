#jobs/scheduler.py
"""
Jobs package for scheduled tasks and cleanup operations
Günlük temizlik: Her gün 03:00'da
Sağlık kontrolü: Her saat
**DB
"""
import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Dict, Callable, Any, Optional
from aiogram import Bot

from config import SCHEDULER_ENABLED  # Yeni eklenen ayar
from .cleanup import cleanup_manager
from utils.metrics import set_active_processes, increment_db_operation
from utils.gmail_client import gmail_client
from utils.smtp_client import smtp_client

logger = logging.getLogger(__name__)

class TaskScheduler:
    """Zamanlanmış görev yöneticisi"""
    
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.scheduled_jobs: Dict[str, Dict] = {}
        self.is_running = False
        self.enabled = SCHEDULER_ENABLED
    
    async def start(self, bot: Bot = None):
        """Zamanlayıcıyı başlat"""
        try:
            if not self.enabled:
                logger.info("🛑 Scheduler is disabled via environment variable")
                return
            
            self.is_running = True
            self.bot = bot
            
            # Zamanlanmış görevleri ayarla
            self._setup_scheduled_jobs()
            
            # Görevleri başlat
            await self._start_scheduled_tasks()
            
            logger.info("✅ Task scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    # ... (diğer metodlar aynı kalacak) ...

from .cleanup import (
    cleanup_manager,
    cleanup_temp_files,
    cleanup_old_logs,
    cleanup_database,
    perform_complete_cleanup
)

from .scheduler import (
    task_scheduler,
    scheduler,
    stop_scheduler
)

__all__ = [
    'cleanup_manager',
    'cleanup_temp_files',
    'cleanup_old_logs',
    'cleanup_database',
    'perform_complete_cleanup',
    'task_scheduler',
    'scheduler',
    'stop_scheduler'
]


# Global instance
task_scheduler = TaskScheduler()

# Backward compatibility
async def scheduler(bot: Bot = None):
    """Zamanlayıcıyı başlat (ana uygulama için)"""
    await task_scheduler.start(bot)
    return task_scheduler
