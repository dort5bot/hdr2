#handlers/dar_handler.py
import logging
import os
import zipfile
import tempfile
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import FSInputFile

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("dar"))
async def dar_cmd(message: Message):
    """Klasör yapısını göster"""
    try:
        structure = generate_folder_structure(".")
        await message.answer(f"📁 **Klasör Yapısı**\n\n```\n{structure}\n```")
    except Exception as e:
        logger.error(f"Dar error: {e}")
        await message.answer("❌ Klasör yapısı gösterilemedi")

@router.message(Command("dar_k"))
async def dar_k_cmd(message: Message):
    """Komut listesini göster"""
    try:
        commands = (
            "📋 **Komut Listesi**\n\n"
            "📊 **Genel Komutlar:**\n"
            "/start - Yardım menüsü\n"
            "/help - Detaylı yardım\n"
            "/status - Sistem durumu\n"
            "/rapor - İşlem raporu\n\n"
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
            "/cleanup - Temizlik yap\n\n"
            "🐛 **Debug Komutları:**\n"
            "/debug_system - Sistem kaynakları\n"
            "/debug_db - Veritabanı istatistikleri\n"
            "/debug_queue - İşlem kuyruğu\n"
            "/debug_config - Config ayarları\n"
            "/debug_test_smtp - SMTP testi\n"
            "/debug_test_gmail - Gmail testi\n"
            "/debug_test_excel - Excel testi\n\n"
            "📁 **Dosya Komutları:**\n"
            "/dar - Klasör yapısı\n"
            "/dar k - Bu liste\n"
            "/dar z - Proje zip\n"
            "/dar t - Kaynak kodu\n"
            "/dar f - Önbellek temizle"
        )
        await message.answer(commands)
    except Exception as e:
        logger.error(f"Dar k error: {e}")
        await message.answer("❌ Komut listesi gösterilemedi")

@router.message(Command("dar_z"))
async def dar_z_cmd(message: Message):
    """Projeyi zip olarak gönder"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            with zipfile.ZipFile(tmp.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk("."):
                    for file in files:
                        if any(ignore in root for ignore in ['.git', '__pycache__', 'venv']):
                            continue
                        if file.endswith(('.py', '.txt', '.json', '.md')):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, ".")
                            zipf.write(file_path, arcname)
            
            zip_file = FSInputFile(tmp.name, filename="project.zip")
            await message.answer_document(zip_file, caption="📦 Proje ZIP dosyası")
            
        os.unlink(tmp.name)
    except Exception as e:
        logger.error(f"Dar z error: {e}")
        await message.answer("❌ ZIP oluşturulamadı")

@router.message(Command("dar_t"))
async def dar_t_cmd(message: Message):
    """Kaynak kodunu txt olarak gönder"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w', encoding='utf-8') as tmp:
            for root, dirs, files in os.walk("."):
                for file in files:
                    if any(ignore in root for ignore in ['.git', '__pycache__', 'venv']):
                        continue
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        tmp.write(f"\n\n{'='*50}\n# {file_path}\n{'='*50}\n\n")
                        with open(file_path, 'r', encoding='utf-8') as f:
                            tmp.write(f.read())
            
            txt_file = FSInputFile(tmp.name, filename="source_code.txt")
            await message.answer_document(txt_file, caption="📄 Kaynak Kodu")
            
        os.unlink(tmp.name)
    except Exception as e:
        logger.error(f"Dar t error: {e}")
        await message.answer("❌ TXT oluşturulamadı")

@router.message(Command("dar_f"))
async def dar_f_cmd(message: Message):
    """Önbelleği temizle"""
    try:
        # Burada önbellek temizleme işlemleri yapılabilir
        await message.answer("✅ Önbellek temizlendi (simüle edildi)")
    except Exception as e:
        logger.error(f"Dar f error: {e}")
        await message.answer("❌ Önbellek temizlenemedi")

def generate_folder_structure(path, prefix=""):
    """Klasör yapısını oluştur"""
    structure = ""
    if os.path.isdir(path):
        items = sorted(os.listdir(path))
        for i, item in enumerate(items):
            if item.startswith('.') or item in ['__pycache__', 'venv']:
                continue
                
            full_path = os.path.join(path, item)
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            
            structure += prefix + connector + item + "\n"
            
            if os.path.isdir(full_path):
                new_prefix = prefix + ("    " if is_last else "│   ")
                structure += generate_folder_structure(full_path, new_prefix)
    
    return structure
