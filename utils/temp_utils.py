# utils/temp_utils.py

import os
import shutil

TEMP_DIR = "temp"

def cleanup_temp_files():
    """Temp klasörünü temizle"""
    for filename in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"[cleanup_temp_files] Hata: {file_path} silinemedi: {e}")

def get_temp_file_count() -> int:
    """Temp klasöründeki dosya sayısı"""
    try:
        return len([f for f in os.listdir(TEMP_DIR) if os.path.isfile(os.path.join(TEMP_DIR, f))])
    except FileNotFoundError:
        return 0

def get_temp_dir_size() -> int:
    """Temp klasörünün boyutu (byte)"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(TEMP_DIR):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
    except FileNotFoundError:
        return 0
    return total_size
