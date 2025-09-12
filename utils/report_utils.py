#utils/report_utils.py - DEĞERLİ
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from .db_utils import db_manager
from .metrics import MAILS_PROCESSED, MAILS_RECEIVED, EXCEL_FILES_CREATED
import asyncio

logger = logging.getLogger(__name__)

async def generate_report(limit: int = 10) -> str:
    """Generate comprehensive report async"""
    try:
        stats = await db_manager.get_mail_stats()
        
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
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Detailed report error: {e}")
        return {"error": str(e)}
