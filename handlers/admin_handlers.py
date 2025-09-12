#handlers/admin_handlers.py
import logging
import json
import psutil
import sqlite3
import os
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS, GROUPS_FILE, groups, source_emails, save_groups
from utils.file_utils import cleanup_temp
from utils.smtp_client import test_smtp_connection
from utils.gmail_client import test_gmail_connection

router = Router()
admin_filter = F.from_user.id.in_(ADMIN_IDS)
logger = logging.getLogger(__name__)

class GroupStates(StatesGroup):
    waiting_for_group_name = State()
    waiting_for_group_email = State()
    waiting_for_group_cities = State()

class SourceStates(StatesGroup):
    waiting_for_source_email = State()

# Grup Yönetimi Komutları
@router.message(Command("gruplar"), admin_filter)
async def list_groups_cmd(message: Message):
    """Kayıtlı grupları listele"""
    try:
        if not groups:
            await message.answer("📭 Kayıtlı grup bulunamadı")
            return
        
        response = "📋 **Kayıtlı Gruplar**\n\n"
        for i, group in enumerate(groups, 1):
            response += (
                f"{i}. **{group['no']}** - {group['name']}\n"
                f"   📧 {group['email']}\n"
                f"   🏙️ {group['iller']}\n\n"
            )
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"List groups error: {e}")
        await message.answer("❌ Gruplar listelenemedi")

@router.message(Command("grup_ekle"), admin_filter)
async def add_group_start_cmd(message: Message, state: FSMContext):
    """Yeni grup eklemeye başla"""
    await message.answer("📝 Yeni grup ekleniyor...\n\nGrup numarası girin:")
    await state.set_state(GroupStates.waiting_for_group_name)

@router.message(GroupStates.waiting_for_group_name)
async def process_group_name(message: Message, state: FSMContext):
    """Grup numarasını işle"""
    await state.update_data(no=message.text)
    await message.answer("📧 Grup email adresini girin:")
    await state.set_state(GroupStates.waiting_for_group_email)

@router.message(GroupStates.waiting_for_group_email)
async def process_group_email(message: Message, state: FSMContext):
    """Grup emailini işle"""
    await state.update_data(email=message.text)
    await message.answer("🏙️ Grup illerini (virgülle ayırarak) girin:")
    await state.set_state(GroupStates.waiting_for_group_cities)

@router.message(GroupStates.waiting_for_group_cities)
async def process_group_cities(message: Message, state: FSMContext):
    """Grup illerini işle ve kaydet"""
    try:
        data = await state.get_data()
        new_group = {
            "no": data['no'],
            "name": data['no'],  # İsim olarak da numara kullan
            "email": data['email'],
            "iller": message.text
        }
        
        groups.append(new_group)
        save_groups(groups)
        
        await message.answer(f"✅ Grup başarıyla eklendi: {data['no']}")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Add group error: {e}")
        await message.answer("❌ Grup eklenemedi")
        await state.clear()

@router.message(Command("grup_sil"), admin_filter)
async def delete_group_cmd(message: Message):
    """Grup sil"""
    try:
        if not message.text.strip().count(' ') >= 1:
            await message.answer("❌ Kullanım: /grup_sil <grup_no>")
            return
        
        group_no = message.text.split(' ', 1)[1].strip()
        
        global groups
        groups = [g for g in groups if g['no'] != group_no]
        save_groups(groups)
        
        await message.answer(f"✅ Grup silindi: {group_no}")
        
    except Exception as e:
        logger.error(f"Delete group error: {e}")
        await message.answer("❌ Grup silinemedi")

@router.message(Command("grup_reviz"), admin_filter)
async def edit_group_cmd(message: Message):
    """Grup düzenle"""
    try:
        if not message.text.strip().count(' ') >= 2:
            await message.answer("❌ Kullanım: /grup_reviz <grup_no> <yeni_email>")
            return
        
        parts = message.text.split(' ', 2)
        group_no = parts[1].strip()
        new_email = parts[2].strip()
        
        for group in groups:
            if group['no'] == group_no:
                group['email'] = new_email
                break
        
        save_groups(groups)
        await message.answer(f"✅ Grup güncellendi: {group_no}")
        
    except Exception as e:
        logger.error(f"Edit group error: {e}")
        await message.answer("❌ Grup güncellenemedi")

# Kaynak Yönetimi Komutları
@router.message(Command("kaynak_ekle"), admin_filter)
async def add_source_start_cmd(message: Message, state: FSMContext):
    """Kaynak mail eklemeye başla"""
    await message.answer("📧 Eklemek istediğiniz mail adresini girin:")
    await state.set_state(SourceStates.waiting_for_source_email)

@router.message(SourceStates.waiting_for_source_email)
async def process_source_email(message: Message, state: FSMContext):
    """Kaynak maili işle"""
    try:
        email = message.text.strip()
        if email not in source_emails:
            source_emails.append(email)
            await message.answer(f"✅ Kaynak mail eklendi: {email}")
        else:
            await message.answer("ℹ️ Bu mail zaten kayıtlı")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Add source error: {e}")
        await message.answer("❌ Mail eklenemedi")
        await state.clear()

@router.message(Command("kaynak_sil"), admin_filter)
async def delete_source_cmd(message: Message):
    """Kaynak mail sil"""
    try:
        if not message.text.strip().count(' ') >= 1:
            await message.answer("❌ Kullanım: /kaynak_sil <email>")
            return
        
        email = message.text.split(' ', 1)[1].strip()
        
        global source_emails
        source_emails = [e for e in source_emails if e != email]
        
        await message.answer(f"✅ Kaynak mail silindi: {email}")
        
    except Exception as e:
        logger.error(f"Delete source error: {e}")
        await message.answer("❌ Mail silinemedi")

# Sistem Yönetimi Komutları
@router.message(Command("log"), admin_filter)
async def show_log_cmd(message: Message):
    """Hata loglarını göster"""
    try:
        log_file = "logs/bot.log"
        if not os.path.exists(log_file):
            await message.answer("📭 Log dosyası bulunamadı")
            return
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-10:]  # Son 10 satır
        
        if not lines:
            await message.answer("📭 Log kaydı bulunamadı")
            return
        
        response = "📋 **Son Hata Logları**\n\n```\n"
        response += "".join(lines)
        response += "\n```"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Show log error: {e}")
        await message.answer("❌ Loglar gösterilemedi")

@router.message(Command("cleanup"), admin_filter)
async def cleanup_cmd(message: Message):
    """Temizlik yap"""
    try:
        await cleanup_temp()
        await message.answer("✅ Temizlik tamamlandı")
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        await message.answer("❌ Temizlik yapılamadı")

# Debug Komutları
@router.message(Command("debug_system"), admin_filter)
async def debug_system_cmd(message: Message):
    """Sistem kaynak kullanımını göster"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        response = (
            "🖥️ **Sistem Durumu**\n\n"
            f"• CPU: {cpu_percent}%\n"
            f"• RAM: {memory.percent}% ({memory.used / (1024**3):.1f}GB / {memory.total / (1024**3):.1f}GB)\n"
            f"• Disk: {disk.percent}% ({disk.used / (1024**3):.1f}GB / {disk.total / (1024**3):.1f}GB)\n"
            f"• Çalışma süresi: {get_uptime()}\n"
        )
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Debug system error: {e}")
        await message.answer("❌ Sistem bilgileri alınamadı")

@router.message(Command("debug_db"), admin_filter)
async def debug_db_cmd(message: Message):
    """Veritabanı istatistiklerini göster"""
    try:
        conn = sqlite3.connect('data/database.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM mails")
        total_mails = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mails WHERE status='pending'")
        pending_mails = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mails WHERE status='success'")
        success_mails = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mails WHERE status='failed'")
        failed_mails = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM logs")
        total_logs = cursor.fetchone()[0]
        
        db_size = os.path.getsize('data/database.db') / (1024 * 1024)
        
        response = (
            "🗃️ **Veritabanı İstatistikleri**\n\n"
            f"• Toplam mail: {total_mails}\n"
            f"• Bekleyen: {pending_mails}\n"
            f"• Başarılı: {success_mails}\n"
            f"• Başarısız: {failed_mails}\n"
            f"• Toplam log: {total_logs}\n"
            f"• DB boyutu: {db_size:.2f} MB\n"
        )
        
        await message.answer(response)
        conn.close()
        
    except Exception as e:
        logger.error(f"Debug db error: {e}")
        await message.answer("❌ Veritabanı bilgileri alınamadı")

@router.message(Command("debug_queue"), admin_filter)
async def debug_queue_cmd(message: Message):
    """İşlem kuyruğu durumunu göster"""
    try:
        from utils.db_utils import get_pending_mails
        
        pending_mails = get_pending_mails()
        response = (
            "📋 **İşlem Kuyruğu**\n\n"
            f"• Bekleyen işlem: {len(pending_mails)}\n"
        )
        
        if pending_mails:
            response += "• Son 5 mail:\n"
            for i, mail in enumerate(pending_mails[:5], 1):
                response += f"  {i}. {mail['message_id'][:20]}...\n"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Debug queue error: {e}")
        await message.answer("❌ Kuyruk bilgileri alınamadı")

@router.message(Command("debug_config"), admin_filter)
async def debug_config_cmd(message: Message):
    """Config ayarlarını göster (şifreler hariç)"""
    try:
        from config import IMAP_SERVER, IMAP_PORT, SMTP_SERVER, SMTP_PORT
        
        response = (
            "⚙️ **Config Ayarları**\n\n"
            f"• IMAP Server: {IMAP_SERVER}:{IMAP_PORT}\n"
            f"• SMTP Server: {SMTP_SERVER}:{SMTP_PORT}\n"
            f"• Kaynak Mailler: {len(source_emails)}\n"
            f"• Grup Sayısı: {len(groups)}\n"
            f"• Admin Sayısı: {len(ADMIN_IDS)}\n"
        )
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Debug config error: {e}")
        await message.answer("❌ Config bilgileri alınamadı")

@router.message(Command("debug_groups"), admin_filter)
async def debug_groups_cmd(message: Message):
    """Grup yapılandırmasını detaylı göster"""
    try:
        response = "📊 **Grup Detayları**\n\n"
        
        for group in groups:
            response += (
                f"• {group['no']}:\n"
                f"  📧 {group['email']}\n"
                f"  🏙️ {group['iller']}\n\n"
            )
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Debug groups error: {e}")
        await message.answer("❌ Grup bilgileri alınamadı")

@router.message(Command("debug_sources"), admin_filter)
async def debug_sources_cmd(message: Message):
    """Kaynak mail listesini göster"""
    try:
        response = "📧 **Kaynak Mail Listesi**\n\n"
        
        for i, email in enumerate(source_emails, 1):
            response += f"{i}. {email}\n"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Debug sources error: {e}")
        await message.answer("❌ Kaynak bilgileri alınamadı")

@router.message(Command("debug_test_smtp"), admin_filter)
async def debug_test_smtp_cmd(message: Message):
    """SMTP bağlantı testi"""
    try:
        result = await test_smtp_connection()
        await message.answer(f"✅ SMTP Testi: {result}")
        
    except Exception as e:
        logger.error(f"Debug SMTP test error: {e}")
        await message.answer(f"❌ SMTP Hatası: {str(e)}")

@router.message(Command("debug_test_gmail"), admin_filter)
async def debug_test_gmail_cmd(message: Message):
    """Gmail bağlantı testi"""
    try:
        result = await test_gmail_connection()
        await message.answer(f"✅ Gmail Testi: {result}")
        
    except Exception as e:
        logger.error(f"Debug Gmail test error: {e}")
        await message.answer(f"❌ Gmail Hatası: {str(e)}")

@router.message(Command("debug_test_excel"), admin_filter)
async def debug_test_excel_cmd(message: Message):
    """Excel işleme testi"""
    try:
        from utils.excel_utils import process_excel_files
        
        results = await process_excel_files()
        response = "✅ **Excel Test Sonucu**\n\n"
        
        if results:
            for group_no, filepaths in results.items():
                response += f"• {group_no}: {len(filepaths)} dosya\n"
        else:
            response += "📭 İşlenecek Excel bulunamadı"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Debug Excel test error: {e}")
        await message.answer(f"❌ Excel Test Hatası: {str(e)}")

# Yardımcı fonksiyonlar
def get_uptime():
    """Sistem çalışma süresini hesapla"""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return f"{hours}sa {minutes}dak"
    except:
        return "Bilinmiyor"
