# jobs/cleanup.py
"""
🔧 CleanupManager Özellikleri:
Temp dosya temizliği: 24 saatten eski dosyalar
Log temizliği: 7 günden eski loglar
DB temizliği: 30 günden eski kayıtlar
Tam temizlik: Tümünü tek seferde yapma
"""
import asyncio
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from config import TEMP_DIR, LOGS_DIR, DATA_DIR
from utils.file_utils import delete_file_async
from utils.db_utils import db_manager
from utils.metrics import increment_db_operation

from temp import cleanup_temp_files, get_temp_file_count, get_temp_dir_size

logger = logging.getLogger(__name__)

class CleanupManager:
    """Temizlik yöneticisi - Temp dosyaları ve eski logları temizler"""
    
    def __init__(self):
        self.temp_dir = Path(TEMP_DIR)
        self.logs_dir = Path(LOGS_DIR)
        self.data_dir = Path(DATA_DIR)
        
    async def cleanup_temp_files(self, older_than_hours: int = 24) -> int:
        """
        Belirtilen saatten eski temp dosyalarını temizler
        
        Args:
            older_than_hours: Kaç saatten eski dosyalar silinecek
            
        Returns:
            Silinen dosya sayısı
        """
        try:
            if not self.temp_dir.exists():
                logger.warning("Temp directory does not exist")
                return 0
            
            deleted_count = 0
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            
            for item in self.temp_dir.iterdir():
                try:
                    # Dosya yaşını kontrol et
                    modified_time = datetime.fromtimestamp(item.stat().st_mtime)
                    if modified_time < cutoff_time:
                        if item.is_file():
                            await delete_file_async(str(item))
                            deleted_count += 1
                            logger.debug(f"Deleted temp file: {item.name}")
                        elif item.is_dir():
                            await asyncio.to_thread(shutil.rmtree, item)
                            deleted_count += 1
                            logger.debug(f"Deleted temp directory: {item.name}")
                except Exception as e:
                    logger.error(f"Error deleting {item}: {e}")
            
            logger.info(f"Temp cleanup completed: {deleted_count} items deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Temp cleanup error: {e}")
            return 0
    
    async def cleanup_old_logs(self, older_than_days: int = 7) -> int:
        """
        Belirtilen günden eski log dosyalarını temizler
        
        Args:
            older_than_days: Kaç günden eski loglar silinecek
            
        Returns:
            Silinen log dosyası sayısı
        """
        try:
            if not self.logs_dir.exists():
                logger.warning("Logs directory does not exist")
                return 0
            
            deleted_count = 0
            cutoff_time = datetime.now() - timedelta(days=older_than_days)
            
            for log_file in self.logs_dir.glob("*.log*"):
                try:
                    # Log dosyası yaşını kontrol et
                    modified_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if modified_time < cutoff_time:
                        await delete_file_async(str(log_file))
                        deleted_count += 1
                        logger.debug(f"Deleted old log: {log_file.name}")
                except Exception as e:
                    logger.error(f"Error deleting log {log_file}: {e}")
            
            logger.info(f"Log cleanup completed: {deleted_count} files deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Log cleanup error: {e}")
            return 0
    
    async def cleanup_database(self, older_than_days: int = 30) -> int:
        """
        Eski veritabanı kayıtlarını temizler
        
        Args:
            older_than_days: Kaç günden eski kayıtlar silinecek
            
        Returns:
            Silinen kayıt sayısı
        """
        try:
            deleted_count = 0
            cutoff_date = (datetime.now() - timedelta(days=older_than_days)).strftime("%Y-%m-%d")
            
            # Başarılı eski mailleri sil
            deleted_count += await self._delete_old_records(
                "mails", 
                "status = 'success' AND created_at < ?", 
                cutoff_date
            )
            
            # Eski log kayıtlarını sil
            deleted_count += await self._delete_old_records(
                "logs", 
                "timestamp < ?", 
                cutoff_date
            )
            
            logger.info(f"Database cleanup completed: {deleted_count} records deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Database cleanup error: {e}")
            return 0
    
    async def _delete_old_records(self, table: str, condition: str, cutoff_date: str) -> int:
        """Eski kayıtları sil"""
        try:
            result = await asyncio.to_thread(
                self._delete_old_records_sync, table, condition, cutoff_date
            )
            increment_db_operation('cleanup')
            return result
        except Exception as e:
            logger.error(f"Error deleting records from {table}: {e}")
            return 0
    
    def _delete_old_records_sync(self, table: str, condition: str, cutoff_date: str) -> int:
        """Senkron eski kayıt silme"""
        try:
            with db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {table} WHERE {condition}", (cutoff_date,))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Sync delete error: {e}")
            return 0
    
    async def perform_complete_cleanup(self):
        """Tam temizlik işlemi gerçekleştir"""
        try:
            logger.info("Starting complete cleanup...")
            
            results = await asyncio.gather(
                self.cleanup_temp_files(24),      # 24 saatten eski temp dosyaları
                self.cleanup_old_logs(7),         # 7 günden eski loglar
                self.cleanup_database(30),        # 30 günden eski DB kayıtları
                return_exceptions=True
            )
            
            total_deleted = sum(result for result in results if isinstance(result, int))
            logger.info(f"Complete cleanup finished: {total_deleted} items total")
            
            return total_deleted
            
        except Exception as e:
            logger.error(f"Complete cleanup error: {e}")
            return 0

# Global instance
cleanup_manager = CleanupManager()

# Backward compatibility
async def cleanup_temp_files(hours: int = 24) -> int:
    return await cleanup_manager.cleanup_temp_files(hours)

async def cleanup_old_logs(days: int = 7) -> int:
    return await cleanup_manager.cleanup_old_logs(days)

async def cleanup_database(days: int = 30) -> int:
    return await cleanup_manager.cleanup_database(days)

async def perform_complete_cleanup() -> int:
    return await cleanup_manager.perform_complete_cleanup()
