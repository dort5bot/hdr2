"""
Data package for database and configuration files
"""

import os
from pathlib import Path

# Data directory path
DATA_DIR = Path(__file__).parent

# File paths
GROUPS_FILE = DATA_DIR / "groups.json"
DATABASE_FILE = DATA_DIR / "database.db"
SOURCES_BACKUP_FILE = DATA_DIR / "sources_backup.txt"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True, parents=True)

def ensure_data_files():
    """Ensure all data files exist with default content if needed"""
    # Ensure groups.json exists
    if not GROUPS_FILE.exists():
        from config import DEFAULT_GROUPS, save_groups
        save_groups(DEFAULT_GROUPS)
        print(f"Created default groups file: {GROUPS_FILE}")
    
    # Ensure database exists with tables
    if not DATABASE_FILE.exists():
        from utils.db_utils import DatabaseManager
        db_manager = DatabaseManager()
        db_manager._init_db()
        print(f"Created database file: {DATABASE_FILE}")
    
    # Ensure sources backup exists
    if not SOURCES_BACKUP_FILE.exists():
        SOURCES_BACKUP_FILE.write_text("", encoding='utf-8')
        print(f"Created sources backup file: {SOURCES_BACKUP_FILE}")

# Initialize data files when package is imported
ensure_data_files()

__all__ = ['GROUPS_FILE', 'DATABASE_FILE', 'SOURCES_BACKUP_FILE', 'DATA_DIR']
