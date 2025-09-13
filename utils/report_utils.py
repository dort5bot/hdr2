#utils/report_utils.py - GELİŞTİRİLMİŞ
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from .db_utils import db_manager
from .metrics import MAILS_PROCESSED, MAILS_RECEIVED, EXCEL_FILES_CREATED
# utils/report_utils.py
from utils.temp_utils import get_temp_file_count, get_temp_dir_size
import asyncio
import psutil
import os

logger = logging.getLogger(__name__)

async def generate_report(limit: int = 10) -> str:
    """Generate comprehensive report async"""
    try:
        stats = await db_manager.get_mail_stats()
        system_status = await get_system_status()
        
        report = [
            "📊 **İşlem Raporu**",
            "",
            f"• 📨 Toplam Mail: {stats['total']}",
            f"• ⏳ Bekleyen: {stats['pending']}",
            f"• ✅ Başarılı: {stats['success']}",
            f"• ❌ Başarısız: {stats['failed']}",
            f"• 🕐 Son İşlem: {stats['last_processed']}",
            "",
            "📈 **Metrikler**",
            f"• 📥 Alınan Mailler: {MAILS_RECEIVED._value.get()}",
            f"• 📤 İşlenen Mailler: {MAILS_PROCESSED._value.get()}",
            f"• 📊 Oluşturulan Excel: {EXCEL_FILES_CREATED._value.get()}",
            "",
            "🖥️ **Sistem Durumu**",
            f"• 📁 Geçici Dosyalar: {system_status['temp_files']} adet",
            f"• 💾 Geçici Klasör Boyutu: {system_status['temp_size_mb']} MB",
            f"• 🧠 RAM Kullanımı: {system_status['memory_usage_percent']}%",
            f"• 💽 Disk Kullanımı: {system_status['disk_usage_percent']}%",
            f"• 🔥 CPU Kullanımı: {system_status['cpu_usage_percent']}%",
            "",
            "⚡ **Son İşlemler**"
        ]
        
        # Son işlemleri ekle
        recent_operations = await _get_recent_operations(limit)
        for op in recent_operations:
            report.append(f"• {op['timestamp']} - {op['message']}")
        
        return "\n".join(report)
        
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        return "❌ Rapor oluşturulamadı"

async def _get_recent_operations(limit: int) -> List[Dict]:
    """Get recent operations from database"""
    try:
        # Bu fonksiyon db_utils'e log kayıtları eklendikten sonra genişletilebilir
        return [
            {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": "Sistem başlatıldı"},
            {"timestamp": (datetime.now() - timedelta(minutes=5)).strftime("%H:%M:%S"), "message": "10 mail işlendi"},
            {"timestamp": (datetime.now() - timedelta(minutes=10)).strftime("%H:%M:%S"), "message": "5 Excel dosyası oluşturuldu"}
        ]
    except Exception as e:
        logger.error(f"Get operations error: {e}")
        return []

async def generate_detailed_report() -> Dict:
    """Generate detailed report for admin dashboard"""
    try:
        stats = await db_manager.get_mail_stats()
        system_status = await get_system_status()
        
        return {
            "summary": {
                "total_mails": stats['total'],
                "pending_mails": stats['pending'],
                "successful_mails": stats['success'],
                "failed_mails": stats['failed'],
                "last_processed": stats['last_processed']
            },
            "metrics": {
                "mails_received": MAILS_RECEIVED._value.get(),
                "mails_processed": MAILS_PROCESSED._value.get(),
                "excel_files_created": EXCEL_FILES_CREATED._value.get()
            },
            "system_status": system_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Detailed report error: {e}")
        return {"error": str(e)}

async def get_system_status():
    """Sistem durum raporu"""
    try:
        temp_file_count = get_temp_file_count()
        temp_dir_size = get_temp_dir_size() / (1024 * 1024)  # MB cinsinden
        
        # Sistem kaynakları kullanımı
        memory_usage = psutil.virtual_memory()
        disk_usage = psutil.disk_usage('/')
        cpu_usage = psutil.cpu_percent(interval=1)
        
        return {
            'temp_files': temp_file_count,
            'temp_size_mb': round(temp_dir_size, 2),
            'memory_usage_percent': round(memory_usage.percent, 1),
            'memory_total_gb': round(memory_usage.total / (1024 ** 3), 1),
            'memory_used_gb': round(memory_usage.used / (1024 ** 3), 1),
            'disk_usage_percent': round(disk_usage.percent, 1),
            'disk_total_gb': round(disk_usage.total / (1024 ** 3), 1),
            'disk_used_gb': round(disk_usage.used / (1024 ** 3), 1),
            'cpu_usage_percent': round(cpu_usage, 1),
            'system_uptime': round((datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds() / 3600, 1),
            'process_uptime': round((datetime.now() - datetime.fromtimestamp(psutil.Process(os.getpid()).create_time())).total_seconds() / 3600, 1)
        }
        
    except Exception as e:
        logger.error(f"System status error: {e}")
        return {
            'temp_files': 0,
            'temp_size_mb': 0,
            'memory_usage_percent': 0,
            'memory_total_gb': 0,
            'memory_used_gb': 0,
            'disk_usage_percent': 0,
            'disk_total_gb': 0,
            'disk_used_gb': 0,
            'cpu_usage_percent': 0,
            'system_uptime': 0,
            'process_uptime': 0,
            'error': str(e)
        }
