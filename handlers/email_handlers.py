# handlers/email_handlers.py
#DB olmadan bu kod ÇALIŞMAZ! ❌
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config import ADMIN_IDS, groups
from utils.gmail_client import check_email
from utils.excel_utils import process_excel_files, create_group_excel
from utils.smtp_client import send_email_with_smtp
from utils.database import add_mail_to_db, update_mail_status, get_pending_mails, get_failed_mails
from utils.group_manager import group_manager



router = Router()
admin_filter = F.from_user.id.in_(ADMIN_IDS)
logger = logging.getLogger(__name__)  # Düzeltildi: name → __name__

# Thread pool for CPU-intensive operations
thread_pool = ThreadPoolExecutor(max_workers=4)

async def process_single_mail(mail):
    """Tek bir maili işler (async olarak)"""
    try:
        filepath = mail["file_path"]
        from_email = mail["from_email"]
        
        logger.info(f"Mail işleniyor: {mail['message_id']} from {from_email}")
        
        # Excel dosyalarını işle
        results = await process_excel_files([filepath])
        
        if not results:
            logger.warning(f"Mail {mail['message_id']} için işlenecek Excel bulunamadı")
            update_mail_status(mail["message_id"], "failed")
            return False, mail["message_id"], "Excel bulunamadı"
        
        send_tasks = []
        sent_groups = []
        
        # Her grup için Excel oluştur ve gönder
        for group_no, filepaths in results.items():
            try:
                output_path = await create_group_excel(group_no, filepaths)
                
                if output_path:
                    # Grup mail adresini bul
                    group = group_manager.get_group_by_no(group_no)
                    if group and group.get("email"):
                        # Asenkron mail gönderme task'ı oluştur
                        subject = f"{group_no} Excel Dosyası"
                        body = f"{group_no} için Excel dosyası ekte gönderilmiştir.\n\nKaynak: {from_email}"
                        
                        task = asyncio.create_task(
                            send_email_with_smtp(group["email"], subject, body, output_path)
                        )
                        send_tasks.append((task, group_no))
                    else:
                        logger.warning(f"{group_no} için mail adresi bulunamadı")
            except Exception as e:
                logger.error(f"{group_no} için Excel oluşturma hatası: {e}")
        
        # Tüm mail gönderme işlemlerini bekleyelim
        if send_tasks:
            tasks = [task for task, _ in send_tasks]
            group_nos = [group_no for _, group_no in send_tasks]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"{group_nos[i]} mail gönderme hatası: {result}")
                elif result:
                    sent_groups.append(group_nos[i])
                    logger.info(f"Mail gönderildi: {group_nos[i]}")
        
        # Durumu güncelle
        if sent_groups:
            update_mail_status(mail["message_id"], "success")
            return True, mail["message_id"], f"{len(sent_groups)} gruba gönderildi ({', '.join(sent_groups)})"
        else:
            update_mail_status(mail["message_id"], "failed")
            return False, mail["message_id"], "Hiçbir gruba gönderilemedi"
            
    except Exception as e:
        logger.error(f"Mail işleme hatası {mail['message_id']}: {e}")
        update_mail_status(mail["message_id"], "failed")
        return False, mail["message_id"], str(e)

@router.message(Command("checkmail"), admin_filter)
async def checkmail_cmd(message: Message):
    """Gmail'i kontrol et ve yeni mailleri işleme kuyruğuna al"""
    try:
        await message.answer("📧 Gmail kontrol ediliyor...")
        
        new_files = await check_email()
        
        if not new_files:
            await message.answer("📭 Yeni mail bulunamadı")
            return
        
        # Mailleri veritabanına ekle
        added_count = 0
        skipped_count = 0
        
        for filepath, from_email, subject in new_files:
            if add_mail_to_db(from_email, filepath, "pending", subject):
                added_count += 1
                logger.info(f"Mail eklendi: {from_email} - {subject}")
            else:
                skipped_count += 1
                logger.warning(f"Mail zaten var: {from_email} - {subject}")
        
        response = f"✅ {added_count} yeni mail işlem kuyruğuna eklendi"
        if skipped_count > 0:
            response += f"\n⏭️ {skipped_count} mail zaten mevcut (atlandı)"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Checkmail error: {e}")
        await message.answer(f"❌ Hata: {str(e)}")

@router.message(Command("process"), admin_filter)
async def process_cmd(message: Message):
    """Bekleyen mailleri işle ve gönder (detaylı feedback ile)"""
    try:
        pending_mails = get_pending_mails()
        
        if not pending_mails:
            await message.answer("⏳ İşlenecek mail bulunamadı")
            return
        
        status_msg = await message.answer(
            f"🔄 {len(pending_mails)} mail işleniyor...\n"
            f"0/{len(pending_mails)} tamamlandı\n"
            f"⏳ Başlatılıyor..."
        )
        
        success_count = 0
        failed_count = 0
        success_details = []
        failed_details = []
        
        for i, mail in enumerate(pending_mails, 1):
            try:
                # Progress güncelleme (her 3 mailde bir veya son mailde)
                if i % 3 == 0 or i == len(pending_mails):
                    await status_msg.edit_text(
                        f"🔄 {len(pending_mails)} mail işleniyor...\n"
                        f"{i}/{len(pending_mails)} tamamlandı\n"
                        f"✅ Başarılı: {success_count} | ❌ Başarısız: {failed_count}"
                    )
                
                # Mail işleme
                success, mail_id, detail = await process_single_mail(mail)
                
                if success:
                    success_count += 1
                    success_details.append(f"✓ {mail_id}: {detail}")
                else:
                    failed_count += 1
                    failed_details.append(f"✗ {mail_id}: {detail}")
                    
            except Exception as e:
                logger.error(f"Mail döngü işleme hatası {mail.get('message_id', 'unknown')}: {e}")
                failed_count += 1
                failed_details.append(f"✗ {mail.get('message_id', 'unknown')}: {str(e)}")
        
        # Detaylı sonuç mesajı
        result_message = (
            f"✅ İşlem tamamlandı:\n"
            f"• 📊 Toplam: {len(pending_mails)}\n"
            f"• ✅ Başarılı: {success_count}\n"
            f"• ❌ Başarısız: {failed_count}\n"
        )
        
        if success_details:
            result_message += f"\n📨 Gönderilenler ({min(3, len(success_details))} örnek):\n"
            for detail in success_details[:3]:
                result_message += f"   {detail}\n"
            if len(success_details) > 3:
                result_message += f"   ...ve {len(success_details) - 3} diğer başarılı işlem"
        
        if failed_details:
            result_message += f"\n\n⚠️ Hatalar ({min(2, len(failed_details))} örnek):\n"
            for detail in failed_details[:2]:
                result_message += f"   {detail}\n"
            if len(failed_details) > 2:
                result_message += f"   ...ve {len(failed_details) - 2} diğer hata"
        
        await message.answer(result_message)
        
    except Exception as e:
        logger.error(f"Process error: {e}")
        await message.answer(f"❌ İşlem hatası: {str(e)}")

@router.message(Command("process_batch"), admin_filter)
async def process_batch_cmd(message: Message):
    """Batch processing ile mailleri paralel işle"""
    try:
        pending_mails = get_pending_mails()
        
        if not pending_mails:
            await message.answer("⏳ İşlenecek mail bulunamadı")
            return
        
        status_msg = await message.answer(
            f"⚡ {len(pending_mails)} mail paralel işlemle işleniyor...\n"
            f"⏳ Başlatılıyor..."
        )
        
        # Tüm mailleri paralel işle
        tasks = [process_single_mail(mail) for mail in pending_mails]
        results = await asyncio.gather(*tasks)
        
        success_count = sum(1 for success, _, _ in results if success)
        failed_count = len(results) - success_count
        
        success_details = [detail for success, _, detail in results if success]
        failed_details = [detail for success, _, detail in results if not success]
        
        # Sonuç mesajı
        result_message = (
            f"⚡ Paralel işlem tamamlandı:\n"
            f"• 📊 Toplam: {len(results)}\n"
            f"• ✅ Başarılı: {success_count}\n"
            f"• ❌ Başarısız: {failed_count}\n"
        )
        
        if success_count > 0:
            result_message += f"• 🚀 Performans: {success_count/len(results)*100:.1f}% başarı\n"
        
        if success_details and len(success_details) <= 5:
            result_message += f"\n📨 Gönderilenler:\n"
            for detail in success_details[:5]:
                result_message += f"   • {detail}\n"
        
        if failed_details and len(failed_details) <= 3:
            result_message += f"\n⚠️ Hatalar:\n"
            for detail in failed_details[:3]:
                result_message += f"   • {detail}\n"
        
        await status_msg.edit_text(result_message)
        
    except Exception as e:
        logger.error(f"Batch process error: {e}")
        await message.answer(f"❌ Paralel işlem hatası: {str(e)}")

@router.message(Command("process_ex"), admin_filter)
async def process_ex_cmd(message: Message):
    """Sadece Excel işleme (gönderme yapmaz)"""
    try:
        # Geçici olarak bir dosya yolu kullanarak test et
        # Gerçek uygulamada bu, belirli dosya yollarını almalı
        await message.answer("📊 Excel işleme başlatılıyor...")
        
        # Örnek dosya yolları - gerçek uygulamada DB'den alınmalı
        sample_files = ["temp/example1.xlsx", "temp/example2.xlsx"]
        
        results = await process_excel_files(sample_files)
        
        if not results:
            await message.answer("📊 İşlenecek Excel bulunamadı")
            return
        
        response = "✅ Excel işleme tamamlandı:\n"
        total_files = 0
        
        for group_no, filepaths in results.items():
            file_count = len(filepaths)
            total_files += file_count
            response += f"• {group_no}: {file_count} dosya\n"
        
        response += f"\n📁 Toplam: {total_files} dosya, {len(results)} grup"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Process_ex error: {e}")
        await message.answer(f"❌ Excel işleme hatası: {str(e)}")

@router.message(Command("retry_failed"), admin_filter)
async def retry_failed_cmd(message: Message):
    """Başarısız mailleri yeniden dene"""
    try:
        failed_mails = get_failed_mails()
        
        if not failed_mails:
            await message.answer("🔄 Yeniden denenicek mail bulunamadı")
            return
        
        # Durumu pending yap
        retry_count = 0
        for mail in failed_mails:
            if update_mail_status(mail["message_id"], "pending"):
                retry_count += 1
                logger.info(f"Mail yeniden deneme kuyruğuna alındı: {mail['message_id']}")
        
        await message.answer(
            f"✅ {retry_count} başarısız mail yeniden işlem kuyruğuna alındı\n"
            f"📋 Toplam başarısız mail: {len(failed_mails)}\n"
            f"🔄 Yeniden deneniyor: {retry_count}"
        )
        
    except Exception as e:
        logger.error(f"Retry failed error: {e}")
        await message.answer(f"❌ Yeniden deneme hatası: {str(e)}")

@router.message(Command("mail_stats"), admin_filter)
async def mail_stats_cmd(message: Message):
    """Mail istatistiklerini göster"""
    try:
        from utils.database import get_mail_stats
        
        stats = get_mail_stats()
        
        response = (
            f"📊 Mail İstatistikleri:\n"
            f"• 📨 Toplam: {stats.get('total', 0)}\n"
            f"• ✅ Başarılı: {stats.get('success', 0)}\n"
            f"• ⏳ Bekleyen: {stats.get('pending', 0)}\n"
            f"• ❌ Başarısız: {stats.get('failed', 0)}\n"
            f"• 🔄 Yeniden Denenecek: {stats.get('failed', 0)}"
        )
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Mail stats error: {e}")
        await message.answer(f"❌ İstatistik hatası: {str(e)}")

@router.message(Command("cleanup"), admin_filter)
async def cleanup_cmd(message: Message):
    """Temizlik işlemleri"""
    try:
        from utils.database import cleanup_old_mails
        from utils.file_utils import cleanup_temp_files
        
        # Eski mailleri temizle
        deleted_count = cleanup_old_mails(days=30)
        
        # Geçici dosyaları temizle
        cleaned_files = cleanup_temp_files()
        
        await message.answer(
            f"🧹 Temizlik tamamlandı:\n"
            f"• 🗑️ {deleted_count} eski mail silindi\n"
            f"• 📁 {cleaned_files} geçici dosya temizlendi"
        )
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        await message.answer(f"❌ Temizlik hatası: {str(e)}")

@router.message(Command("help_mail"), admin_filter)
async def help_mail_cmd(message: Message):
    """Mail komutları için yardım"""
    help_text = """
📧 Mail Yönetim Komutları:

/checkmail - Yeni mailleri kontrol et
/process - Bekleyen mailleri işle (sıralı)
/process_batch - Mailleri paralel işle (hızlı)
/process_ex - Sadece Excel işle (test)
/retry_failed - Başarısız mailleri yeniden dene
/mail_stats - İstatistikleri göster
/cleanup - Eski verileri temizle

⚡ Öneri: Küçük işlemler için /process, büyük işlemler için /process_batch kullanın.
"""
    await message.answer(help_text)

"""
Gerekli Veritabanı Şeması
📁 SQLite kullanıldı (hafif ve kurulum gerektirmiyor)
🔄 Thread-safe değil, production için PostgreSQL önerilir
📊 İstatistikler için DB şart
🔍 Durum takibi (pending/success/failed) için DB şart
🗑️ Temizlik işlemleri için DB şart


CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    from_email VARCHAR(255) NOT NULL,
    subject TEXT,
    file_path TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL,
    error_message TEXT
);

CREATE INDEX idx_emails_status ON emails(status);
CREATE INDEX idx_emails_message_id ON emails(message_id);
"""
