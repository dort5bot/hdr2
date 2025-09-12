"""
Temporary files directory for storing downloaded emails and processed Excel files
"""

import os
from pathlib import Path
import uuid
from datetime import datetime

# Temp directory path
TEMP_DIR = Path(__file__).parent

# Ensure temp directory exists
TEMP_DIR.mkdir(exist_ok=True, parents=True)

def generate_temp_filename(extension: str = "xlsx", prefix: str = "") -> Path:
    """
    Generate a unique temporary filename with UUID and timestamp
    
    Args:
        extension: File extension (default: xlsx)
        prefix: Optional filename prefix
        
    Returns:
        Path object for the temporary file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    if prefix:
        filename = f"{prefix}_{timestamp}_{unique_id}.{extension}"
    else:
        filename = f"{timestamp}_{unique_id}.{extension}"
    
    return TEMP_DIR / filename

def cleanup_temp_files(max_age_hours: int = 24) -> int:
    """
    Clean up temporary files older than specified hours
    
    Args:
        max_age_hours: Maximum age of files in hours
        
    Returns:
        Number of files deleted
    """
    deleted_count = 0
    cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
    
    for file_path in TEMP_DIR.iterdir():
        if file_path.is_file():
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
    
    return deleted_count

def get_temp_file_count() -> int:
    """Get count of files in temp directory"""
    return len([f for f in TEMP_DIR.iterdir() if f.is_file()])

def get_temp_dir_size() -> int:
    """Get total size of temp directory in bytes"""
    total_size = 0
    for file_path in TEMP_DIR.iterdir():
        if file_path.is_file():
            total_size += file_path.stat().st_size
    return total_size

# Initialize temp directory
print(f"Temp directory initialized: {TEMP_DIR}")

__all__ = [
    'TEMP_DIR',
    'generate_temp_filename',
    'cleanup_temp_files',
    'get_temp_file_count',
    'get_temp_dir_size'
]
