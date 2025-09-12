#utils/metrics.py
import time
from prometheus_client import Counter, Histogram, Gauge
from functools import wraps
import asyncio

# Metric tanımlamaları
MAILS_PROCESSED = Counter('mails_processed_total', 'Total processed mails', ['status'])
MAILS_RECEIVED = Counter('mails_received_total', 'Total received mails')
PROCESSING_TIME = Histogram('mail_processing_seconds', 'Time spent processing mail')
EXCEL_FILES_CREATED = Counter('excel_files_created_total', 'Total Excel files created')
SMTP_SEND_SUCCESS = Counter('smtp_send_success_total', 'Successful SMTP sends')
SMTP_SEND_FAILED = Counter('smtp_send_failed_total', 'Failed SMTP sends')
ACTIVE_PROCESSES = Gauge('active_processes', 'Currently active processes')
DB_OPERATIONS = Counter('db_operations_total', 'Total database operations', ['operation'])

# Prometheus metrikleri
TEMP_FILE_COUNT = Gauge('temp_files_total', 'Total temporary files')
TEMP_DIR_SIZE = Gauge('temp_dir_size_bytes', 'Temp directory size in bytes')
TEMP_CLEANUP_COUNT = Counter('temp_cleanup_total', 'Total temp cleanup operations')

def track_processing_time(func):
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        PROCESSING_TIME.observe(time.time() - start_time)
        return result
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        PROCESSING_TIME.observe(time.time() - start_time)
        return result
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

def increment_mails_received():
    MAILS_RECEIVED.inc()

def increment_mails_processed(status='success'):
    MAILS_PROCESSED.labels(status=status).inc()

def increment_excel_files_created(count=1):
    EXCEL_FILES_CREATED.inc(count)

def increment_smtp_success():
    SMTP_SEND_SUCCESS.inc()

def increment_smtp_failed():
    SMTP_SEND_FAILED.inc()

def set_active_processes(count):
    ACTIVE_PROCESSES.set(count)

def increment_db_operation(operation):
    DB_OPERATIONS.labels(operation=operation).inc()
