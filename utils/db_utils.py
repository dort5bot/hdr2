#utils/db_utils.py - KRİTİK ÖNEMDE
import os
import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
from contextlib import contextmanager
from .metrics import increment_db_operation

logger = logging.getLogger(__name__)

import os
import sqlite3
import logging
from contextlib import contextmanager
from .metrics import increment_db_operation  # varsayalım metrics modülün var

logger = logging.getLogger(__name__)

def is_valid_sqlite_file(path: str) -> bool:
    if not os.path.exists(path):
        return True  # Dosya yoksa sorun yok
    try:
        with sqlite3.connect(path) as conn:
            conn.execute("PRAGMA schema_version;")
        return True
    except sqlite3.DatabaseError:
        return False

class DatabaseManager:
    def __init__(self, db_path: str = "data/database.db"):
        self.db_path = db_path
        # Eğer veritabanı klasörü yoksa oluştur
         os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not is_valid_sqlite_file(self.db_path):
            logger.warning(f"{self.db_path} geçerli bir SQLite veritabanı değil. Siliniyor...")
            os.remove(self.db_path)

        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # mails tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mails (
                    message_id TEXT PRIMARY KEY,
                    from_email TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'success', 'failed')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP NULL,
                    error_message TEXT NULL
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mails_status ON mails(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mails_created_at ON mails(created_at)')

            # logs tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL CHECK(level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    module TEXT NULL,
                    context TEXT NULL
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)')

            # processed_files tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_filename TEXT NOT NULL,
                    processed_filename TEXT NOT NULL,
                    group_no TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    row_count INTEGER NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL CHECK(status IN ('success', 'failed')),
                    error_message TEXT NULL
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_processed_files_group ON processed_files(group_no)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_processed_files_date ON processed_files(processed_at)')

            # email_stats tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    total_emails INTEGER DEFAULT 0,
                    processed_emails INTEGER DEFAULT 0,
                    failed_emails INTEGER DEFAULT 0,
                    total_files INTEGER DEFAULT 0,
                    UNIQUE(date)
                )
            ''')

            conn.commit()
            increment_db_operation('init')

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    async def add_mail_to_db(self, from_email: str, file_path: str, status: str = "pending") -> bool:
        """Add mail to database async"""
        try:
            message_id = f"{from_email}_{file_path}"
            return await asyncio.to_thread(
                self._add_mail_sync, message_id, from_email, file_path, status
            )
        except Exception as e:
            logger.error(f"Add mail error: {e}")
            return False

    def _add_mail_sync(self, message_id: str, from_email: str, file_path: str, status: str) -> bool:
        """Sync version of add_mail"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO mails (message_id, from_email, file_path, status)
                VALUES (?, ?, ?, ?)
            ''', (message_id, from_email, file_path, status))
            conn.commit()
            increment_db_operation('insert')
            return cursor.rowcount > 0

    async def update_mail_status(self, message_id: str, status: str) -> bool:
        """Update mail status async"""
        try:
            return await asyncio.to_thread(
                self._update_mail_status_sync, message_id, status
            )
        except Exception as e:
            logger.error(f"Update mail status error: {e}")
            return False

    def _update_mail_status_sync(self, message_id: str, status: str) -> bool:
        """Sync version of update_mail_status"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE mails SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
            ''', (status, message_id))
            conn.commit()
            increment_db_operation('update')
            return cursor.rowcount > 0

    async def get_pending_mails(self) -> List[Dict]:
        """Get pending mails async"""
        try:
            return await asyncio.to_thread(self._get_pending_mails_sync)
        except Exception as e:
            logger.error(f"Get pending mails error: {e}")
            return []

    def _get_pending_mails_sync(self) -> List[Dict]:
        """Sync version of get_pending_mails"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message_id, from_email, file_path 
                FROM mails WHERE status = 'pending'
            ''')
            return [dict(row) for row in cursor.fetchall()]

    async def get_mail_stats(self) -> Dict:
        """Get mail statistics async"""
        try:
            return await asyncio.to_thread(self._get_mail_stats_sync)
        except Exception as e:
            logger.error(f"Get mail stats error: {e}")
            return {}

    def _get_mail_stats_sync(self) -> Dict:
        """Sync version of get_mail_stats"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM mails")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM mails WHERE status = 'pending'")
            pending = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM mails WHERE status = 'success'")
            success = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM mails WHERE status = 'failed'")
            failed = cursor.fetchone()[0]
            
            cursor.execute("SELECT MAX(updated_at) FROM mails WHERE status = 'success'")
            last_processed = cursor.fetchone()[0] or "Never"
            
            return {
                'total': total,
                'pending': pending,
                'success': success,
                'failed': failed,
                'last_processed': last_processed
            }

# Global instance
db_manager = DatabaseManager()

# Backward compatibility functions
def add_mail_to_db(from_email: str, file_path: str, status: str = "pending") -> bool:
    return asyncio.run(db_manager.add_mail_to_db(from_email, file_path, status))

def update_mail_status(message_id: str, status: str) -> bool:
    return asyncio.run(db_manager.update_mail_status(message_id, status))

def get_pending_mails() -> List[Dict]:
    return asyncio.run(db_manager.get_pending_mails())

def get_mail_stats() -> Dict:
    return asyncio.run(db_manager.get_mail_stats())
