#  🚨 DB ŞART
import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database import get_mail_stats
from utils.report_utils import generate_report

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def start_cmd(message: Message):
    """Botu başlat ve yardım menüsü göster"""
    welcome_text = (
        "🤖 **HIDIR Botuna Hoşgeldiniz**\n\n"
        "Bu bot aşağıdaki komutlarla çalışır:\n\n"
        "📊 **Genel Komutlar:**\n"
        "/start - Bu mesajı göster\n"
        "/help - Yardım menüsü\n"
        "/status - Sistem durumu\n"
        "/rapor - Son işlem raporu\n\n"
        "📧 **Mail İşlemleri:**\n"
        "/checkmail - Mailleri kontrol et\n"
        "/process - Mailleri işle\n"
        "/process_ex - Sadece Excel işle\n"
        "/retry_failed - Başarısızları yeniden dene\n\n"
        "⚙️ **Yönetici Komutları:**\n"
        "/gruplar - Grupları listele\n"
        "/grup_ekle - Yeni grup ekle\n"
        "/grup_sil - Grup sil\n"
        "/grup_reviz - Grup düzenle\n"
        "/kaynak_ekle - Kaynak mail ekle\n"
        "/kaynak_sil - Kaynak mail sil\n"
        "/log - Hata loglarını göster\n"
        "/cleanup - Temizlik yap\n"
        "/debug_* - Debug komutları\n\n"
        "📁 **Dosya Komutları:**\n"
        "/dar - Klasör yapısını göster\n"
        "/dar k - Komut listesini göster\n"
        "/dar z - Projeyi zip olarak gönder\n"
        "/dar t - Kaynak kodunu txt olarak gönder\n"
        "/dar f - Önbelleği temizle"
    )
    await message.answer(welcome_text)

@router.message(Command("help"))
async def help_cmd(message: Message):
    """Detaylı yardım menüsü göster"""
    help_text = (
        "🆘 **Yardım Menüsü**\n\n"
        "**📧 Mail İşlem Akışı:**\n"
        "1. /checkmail - Gelen kutunu kontrol et\n"
        "2. /process - Excel'leri işle ve gönder\n"
        "3. /rapor - İşlem sonucunu gör\n\n"
        "**⚙️ Sistem Yönetimi:**\n"
        "• /status - Sistem durumunu gör\n"
        "• /log - Hataları incele\n"
        "• /cleanup - Geçici dosyaları temizle\n\n"
        "**👥 Grup Yönetimi:**\n"
        "• /gruplar - Tüm grupları listele\n"
        "• /grup_ekle - Yeni grup ekle\n"
        "• /grup_sil - Grup sil\n"
        "• /grup_reviz - Grup bilgilerini düzenle\n\n"
        "**📧 Kaynak Yönetimi:**\n"
        "• /kaynak_ekle - Takip edilecek mail ekle\n"
        "• /kaynak_sil - Maili takip listesinden çıkar\n\n"
        "**🐛 Debug Komutları:**\n"
        "/debug_system - Sistem kaynakları\n"
        "/debug_db - Veritabanı istatistikleri\n"
        "/debug_queue - İşlem kuyruğu\n"
        "/debug_config - Config ayarları\n"
        "/debug_test_smtp - SMTP testi\n"
        "/debug_test_gmail - Gmail testi"
    )
    await message.answer(help_text)

@router.message(Command("status"))
async def status_cmd(message: Message):
    """Sistem durumunu göster"""
    try:
        stats = get_mail_stats()
        
        status_text = (
            "📊 **Sistem Durumu**\n\n"
            f"• Toplam Mail: {stats['total']}\n"
            f"• Bekleyen: {stats['pending']}\n"
            f"• Başarılı: {stats['success']}\n"
            f"• Başarısız: {stats['failed']}\n"
            f"• Son İşlem: {stats['last_processed']}\n\n"
            "🔄 **Son Durum:**\n"
            f"{'✅ Sistem aktif' if stats['pending'] == 0 else '⏳ İşlem bekliyor'}"
        )
        
        await message.answer(status_text)
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        await message.answer("❌ Sistem durumu alınamadı")

@router.message(Command("rapor"))
async def rapor_cmd(message: Message):
    """Son işlemlerin raporunu göster"""
    try:
        report = await generate_report(limit=10)
        await message.answer(report)
        
    except Exception as e:
        logger.error(f"Rapor error: {e}")
        await message.answer("❌ Rapor oluşturulamadı")

"""

✅

#  🚨 DB ŞART
SQLite kullanın - Hafif ve kurulum gerektirmeyen bir çözüm
-- Mail istatistikleri için
CREATE TABLE mail_stats (
    id INTEGER PRIMARY KEY,
    total INTEGER DEFAULT 0,
    pending INTEGER DEFAULT 0,
    success INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    last_processed TIMESTAMP
);

-- İşlem geçmişi için
CREATE TABLE process_history (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP,
    status TEXT,
    details TEXT,
    mail_count INTEGER
);
"""
