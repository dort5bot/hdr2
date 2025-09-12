#file_utils.py
import os
import logging
import aiofiles
import asyncio
from pathlib import Path
from typing import List
from config import TEMP_DIR

logger = logging.getLogger(__name__)

async def cleanup_temp():
    """Clean up temp directory asynchronously"""
    try:
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR, exist_ok=True)
            return

        tasks = []
        for filename in os.listdir(TEMP_DIR):
            filepath = os.path.join(TEMP_DIR, filename)
            if os.path.isfile(filepath):
                tasks.append(delete_file_async(filepath))
        
        # Tüm silme işlemlerini paralel yap
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Hataları logla
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"File deletion error: {result}")
        
        logger.info(f"Temp directory cleaned up: {TEMP_DIR}")
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

async def delete_file_async(filepath: str):
    """Asenkron dosya silme"""
    try:
        await asyncio.to_thread(os.unlink, filepath)
        logger.debug(f"Deleted: {filepath}")
    except Exception as e:
        logger.error(f"Error deleting {filepath}: {e}")
        raise

async def ensure_temp_dir():
    """Temp dizinini garanti et"""
    os.makedirs(TEMP_DIR, exist_ok=True)
    return TEMP_DIR

async def list_temp_files(pattern: str = "*") -> List[str]:
    """Temp dizinindeki dosyaları listele"""
    await ensure_temp_dir()
    temp_path = Path(TEMP_DIR)
    return [f.name for f in temp_path.glob(pattern) if f.is_file()]

async def get_file_size(filepath: str) -> int:
    """Dosya boyutunu async olarak al"""
    try:
        return await asyncio.to_thread(os.path.getsize, filepath)
    except Exception as e:
        logger.error(f"File size error: {e}")
        return 0
