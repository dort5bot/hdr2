# utils/database.py - KRİTİK ÖNEMDE
# Tüm SQLite operasyonları burada

import os
import sqlite3
import logging
from typing import List, Dict
from datetime import datetime
import asyncio
from contextlib import contextmanager
from .metrics import increment_db_operation

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

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        if not is_valid_sqlite_file(self.db_path):
            logger.warning(f"{self.db_path} geçerli bir SQLite veritabanı değil. Siliniyor...")
            os.remove(self.db_path)

        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # mails tablosu (handlers ile uyumlu)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT UNIQUE NOT NULL,
                    from_email TEXT NOT NULL,
                    subject TEXT,
                    file_path TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'success', 'failed')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP NULL,
                    error_message TEXT NULL
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mails_status ON mails(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mails_created_at ON mails(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_mails_message_id ON mails(message_id)')

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

            # source_emails tablosu (admin_handlers için)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS source_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    description TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # process_history tablosu (commands için)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS process_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT,
                    details TEXT,
                    mail_count INTEGER
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

    async def add_mail_to_db(self, from_email: str, file_path: str, status: str = "pending", subject: str = None) -> bool:
        try:
            message_id = f"{from_email}_{os.path.basename(file_path)}"
            return await asyncio.to_thread(
                self._add_mail_sync, message_id, from_email, file_path, status, subject
            )
        except Exception as e:
            logger.error(f"Add mail error: {e}")
            return False

    def _add_mail_sync(self, message_id: str, from_email: str, file_path: str, status: str, subject: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO mails (message_id, from_email, file_path, status, subject)
                VALUES (?, ?, ?, ?, ?)
            ''', (message_id, from_email, file_path, status, subject))
            conn.commit()
            increment_db_operation('insert')
            return cursor.rowcount > 0

    async def update_mail_status(self, message_id: str, status: str, error_message: str = None) -> bool:
        try:
            return await asyncio.to_thread(
                self._update_mail_status_sync, message_id, status, error_message
            )
        except Exception as e:
            logger.error(f"Update mail status error: {e}")
            return False

    def _update_mail_status_sync(self, message_id: str, status: str, error_message: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if error_message:
                cursor.execute('''
                    UPDATE mails SET status = ?, processed_at = CURRENT_TIMESTAMP, error_message = ?
                    WHERE message_id = ?
                ''', (status, error_message, message_id))
            else:
                cursor.execute('''
                    UPDATE mails SET status = ?, processed_at = CURRENT_TIMESTAMP
                    WHERE message_id = ?
                ''', (status, message_id))
            conn.commit()
            increment_db_operation('update')
            return cursor.rowcount > 0

    async def get_pending_mails(self) -> List[Dict]:
        try:
            return await asyncio.to_thread(self._get_pending_mails_sync)
        except Exception as e:
            logger.error(f"Get pending mails error: {e}")
            return []

    def _get_pending_mails_sync(self) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message_id, from_email, file_path, subject
                FROM mails WHERE status = 'pending'
            ''')
            return [dict(row) for row in cursor.fetchall()]

    async def get_failed_mails(self) -> List[Dict]:
        try:
            return await asyncio.to_thread(self._get_failed_mails_sync)
        except Exception as e:
            logger.error(f"Get failed mails error: {e}")
            return []

    def _get_failed_mails_sync(self) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message_id, from_email, file_path, subject, error_message
                FROM mails WHERE status = 'failed'
            ''')
            return [dict(row) for row in cursor.fetchall()]

    async def get_mail_stats(self) -> Dict:
        try:
            return await asyncio.to_thread(self._get_mail_stats_sync)
        except Exception as e:
            logger.error(f"Get mail stats error: {e}")
            return {}

    def _get_mail_stats_sync(self) -> Dict:
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

            cursor.execute("SELECT MAX(processed_at) FROM mails WHERE status = 'success'")
            last_processed = cursor.fetchone()[0] or "Never"

            return {
                'total': total,
                'pending': pending,
                'success': success,
                'failed': failed,
                'last_processed': last_processed
            }

    async def cleanup_old_mails(self, days: int = 30) -> int:
        try:
            return await asyncio.to_thread(self._cleanup_old_mails_sync, days)
        except Exception as e:
            logger.error(f"Cleanup old mails error: {e}")
            return 0

    def _cleanup_old_mails_sync(self, days: int) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM mails 
                WHERE created_at < datetime('now', ?)
            ''', (f'-{days} days',))
            deleted_count = cursor.rowcount
            conn.commit()
            increment_db_operation('delete')
            return deleted_count

    async def add_source_email(self, email: str, description: str = None) -> bool:
        try:
            return await asyncio.to_thread(self._add_source_email_sync, email, description)
        except Exception as e:
            logger.error(f"Add source email error: {e}")
            return False

    def _add_source_email_sync(self, email: str, description: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO source_emails (email, description)
                VALUES (?, ?)
            ''', (email, description))
            conn.commit()
            increment_db_operation('insert')
            return cursor.rowcount > 0

    async def remove_source_email(self, email: str) -> bool:
        try:
            return await asyncio.to_thread(self._remove_source_email_sync, email)
        except Exception as e:
            logger.error(f"Remove source email error: {e}")
            return False

    def _remove_source_email_sync(self, email: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM source_emails WHERE email = ?
            ''', (email,))
            conn.commit()
            increment_db_operation('delete')
            return cursor.rowcount > 0

    async def get_all_sources(self) -> List[Dict]:
        try:
            return await asyncio.to_thread(self._get_all_sources_sync)
        except Exception as e:
            logger.error(f"Get all sources error: {e}")
            return []

    def _get_all_sources_sync(self) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT email, description, added_at FROM source_emails ORDER BY added_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    async def add_process_history(self, status: str, details: str, mail_count: int) -> bool:
        try:
            return await asyncio.to_thread(self._add_process_history_sync, status, details, mail_count)
        except Exception as e:
            logger.error(f"Add process history error: {e}")
            return False

    def _add_process_history_sync(self, status: str, details: str, mail_count: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO process_history (status, details, mail_count)
                VALUES (?, ?, ?)
            ''', (status, details, mail_count))
            conn.commit()
            increment_db_operation('insert')
            return cursor.rowcount > 0

    async def get_recent_process_history(self, limit: int = 10) -> List[Dict]:
        try:
            return await asyncio.to_thread(self._get_recent_process_history_sync, limit)
        except Exception as e:
            logger.error(f"Get recent process history error: {e}")
            return []

    def _get_recent_process_history_sync(self, limit: int) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, status, details, mail_count 
                FROM process_history 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

# Global instance
db_manager = DatabaseManager()

# Backward compatibility functions
def add_mail_to_db(from_email: str, file_path: str, status: str = "pending", subject: str = None) -> bool:
    return asyncio.run(db_manager.add_mail_to_db(from_email, file_path, status, subject))

def update_mail_status(message_id: str, status: str, error_message: str = None) -> bool:
    return asyncio.run(db_manager.update_mail_status(message_id, status, error_message))

def get_pending_mails() -> List[Dict]:
    return asyncio.run(db_manager.get_pending_mails())

def get_failed_mails() -> List[Dict]:
    return asyncio.run(db_manager.get_failed_mails())

def get_mail_stats() -> Dict:
    return asyncio.run(db_manager.get_mail_stats())

def cleanup_old_mails(days: int = 30) -> int:
    return asyncio.run(db_manager.cleanup_old_mails(days))

def add_source_email(email: str, description: str = None) -> bool:
    return asyncio.run(db_manager.add_source_email(email, description))

def remove_source_email(email: str) -> bool:
    return asyncio.run(db_manager.remove_source_email(email))

def get_all_sources() -> List[Dict]:
    return asyncio.run(db_manager.get_all_sources())

def add_process_history(status: str, details: str, mail_count: int) -> bool:
    return asyncio.run(db_manager.add_process_history(status, details, mail_count))

def get_recent_process_history(limit: int = 10) -> List[Dict]:
    return asyncio.run(db_manager.get_recent_process_history(limit))
