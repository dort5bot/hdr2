
"""
Utils package for async email processing and file operations
"""

from .file_utils import cleanup_temp, ensure_temp_dir, list_temp_files
from .excel_utils import process_excel_files, create_group_excel, validate_excel_file
from .smtp_client import send_email_with_smtp, test_smtp_connection, smtp_client
from .gmail_client import check_email, test_gmail_connection, gmail_client
from .normalize_utils import normalize_text, normalize_city_name, is_valid_city

# Version info
__version__ = "1.0.0"
__author__ = "Your Name"

# Public API
__all__ = [
    'cleanup_temp',
    'ensure_temp_dir',
    'list_temp_files',
    'process_excel_files',
    'create_group_excel',
    'validate_excel_file',
    'send_email_with_smtp',
    'test_smtp_connection',
    'smtp_client',
    'check_email',
    'test_gmail_connection',
    'gmail_client',
    'normalize_text',
    'normalize_city_name',
    'is_valid_city'
]
