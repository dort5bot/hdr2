#handlers/email_handlers.py
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config import ADMIN_IDS
from utils.gmail_client import check_email
from utils.excel_utils import process_excel_files, create_group_excel
from utils.smtp_client import send_email_with_smtp
from utils.db_utils import add_mail_to_db, update_mail_status, get_pending_mails

router = Router()
admin_filter = F.from_user.id.in_(ADMIN_IDS)
logger = logging.getLogger(__name__)

@router.message(Command("checkmail"), admin_filter)
async def checkmail_cmd(message: Message):
    """Gmail'i kontrol et ve yeni mailleri işleme kuyruğuna al"""
    try:
        new_files = await check_email()
        
        if not new_files:
            await message.answer("📭 Yeni mail bulunamadı")
            return
        
        # Mailleri veritabanına ekle
        added_count = 0
        for filepath, from_email in new_files:
            if add_mail_to_db(from_email, filepath, "pending"):
                added_count += 1
        
        await message.answer(f"✅ {added_count} yeni mail işlem kuyruğuna eklendi")
        
    except Exception as e:
        logger.error(f"Checkmail error: {e}")
        await message.answer(f"❌ Hata: {str(e)}")

@router.message(Command("process"), admin_filter)
async def process_cmd(message: Message):
    """Bekleyen mailleri işle ve gönder"""
    try:
        pending_mails = get_pending_mails()
        
        if not pending_mails:
            await message.answer("⏳ İşlenecek mail bulunamadı")
            return
        
        await message.answer(f"🔄 {len(pending_mails)} mail işleniyor...")
        
        success_count = 0
        failed_count = 0
        
        for mail in pending_mails:
            try:
                # Excel dosyalarını işle
                results = await process_excel_files()
                
                # Gruplara göre Excel oluştur ve gönder
                for group_no, filepaths in results.items():
                    output_path = await create_group_excel(group_no, filepaths)
                    
                    if output_path:
                        # Grup mail adresini bul
                        group_email = None
                        for group in groups:
                            if group["no"] == group_no:
                                group_email = group["email"]
                                break
                        
                        if group_email:
                            # Mail gönder
                            subject = f"{group_no} Excel Dosyası"
                            body = f"{group_no} için Excel dosyası ekte gönderilmiştir."
                            
                            if await send_email_with_smtp(group_email, subject, body, output_path):
                                logger.info(f"Mail gönderildi: {group_email}")
                            else:
                                logger.error(f"Mail gönderilemedi: {group_email}")
                
                # Durumu güncelle
                update_mail_status(mail["message_id"], "success")
                success_count += 1
                
            except Exception as e:
                logger.error(f"Mail işleme hatası {mail['message_id']}: {e}")
                update_mail_status(mail["message_id"], "failed")
                failed_count += 1
        
        await message.answer(
            f"✅ İşlem tamamlandı:\n"
            f"• Başarılı: {success_count}\n"
            f"• Başarısız: {failed_count}"
        )
        
    except Exception as e:
        logger.error(f"Process error: {e}")
        await message.answer(f"❌ Hata: {str(e)}")

@router.message(Command("process_ex"), admin_filter)
async def process_ex_cmd(message: Message):
    """Sadece Excel işleme (gönderme yapmaz)"""
    try:
        results = await process_excel_files()
        
        if not results:
            await message.answer("📊 İşlenecek Excel bulunamadı")
            return
        
        response = "✅ Excel işleme tamamlandı:\n"
        for group_no, filepaths in results.items():
            response += f"• {group_no}: {len(filepaths)} dosya\n"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Process_ex error: {e}")
        await message.answer(f"❌ Hata: {str(e)}")

@router.message(Command("retry_failed"), admin_filter)
async def retry_failed_cmd(message: Message):
    """Başarısız mailleri yeniden dene"""
    try:
        failed_mails = get_failed_mails()
        
        if not failed_mails:
            await message.answer("🔄 Yeniden denenicek mail bulunamadı")
            return
        
        await message.answer(f"🔄 {len(failed_mails)} başarısız mail yeniden deneniyor...")
        
        # Durumu pending yap
        for mail in failed_mails:
            update_mail_status(mail["message_id"], "pending")
        
        await message.answer("✅ Başarısız mailler yeniden işlem kuyruğuna alındı")
        
    except Exception as e:
        logger.error(f"Retry failed error: {e}")
        await message.answer(f"❌ Hata: {str(e)}")
