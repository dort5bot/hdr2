# handlers/dar_handler.py 
# Aiogram 3.x uyumlu
# Router objesi -> handler_loader.py uyumlu
# Komut açıklamaları artık burada (COMMAND_INFO gömülü)
#
"""
/dar → proje dizinini ağaç yapısında listeler. Eğer 4000 karakteri geçerse .txt gönderir.
/dar k → handlers/*.py içindeki komutları tarar, COMMAND_INFO açıklamalarıyla listeler.
/dar Z → tree.txt + filtrelenmiş geçerli dosyaları (py, json, md, csv, .env, .gitignore vb.) içeren .zip oluşturur.
/dar t → tüm geçerli dosyaların içeriklerini tek .txt dosyada gönderir (ayrılmış başlıklarla).
"""

import os
import re
import zipfile
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

load_dotenv()
TELEGRAM_NAME = os.getenv("TELEGRAM_NAME", "xbot")
ROOT_DIR = '.'
TELEGRAM_MSG_LIMIT = 4000

router = Router()

# -----------------------------
# ✅ Komut Açıklamaları (bağımsız)
# -----------------------------
COMMAND_INFO = {
    "dar": "Proje dizin yapısını ağaç şeklinde listeler",
    "fr": "Funding Rate komutu ve günlük CSV kaydı",
    "whale": "Whale Alerts komutu ve günlük CSV kaydı",
    "p": "Anlık fiyat, 24h değişim, hacim bilgisi",
    "p_ekle": "Favori coin listesine ekleme",
    "p_fav": "Favori coinleri listeleme",
    "p_sil": "Favori coin listesinden silme",
    "io": "In-Out alış/satış baskısı raporu",
    "nls": "Balina hareketleri ve yoğunluk (NLS analizi)",
    "npr": "Nakit Piyasa Raporu",
    "eft": "ETF & ABD piyasaları raporu",
    "ap": "Altların Güç Endeksi (AP)",
}
# -----------------------------

EXT_LANG_MAP = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.ts': 'TypeScript',
    '.java': 'Java',
    '.cpp': 'C++',
    '.c': 'C',
    '.html': 'HTML',
    '.css': 'CSS',
    '.json': 'JSON',
    '.csv': 'CSV',
    '.sh': 'Shell',
    '.md': 'Markdown',
    '.txt': 'Text',
}

FILE_INFO = {
    'main.py': ("Ana bot başlatma, handler kayıtları, JobQueue görevleri", None),
    'keep_alive.py': ("Render Free ping sistemi (bot uyumasını önler)", None),
    'io_handler.py': ("/io → In-Out Alış Satış Baskısı raporu", "utils.io_utils"),
    'nls_handler.py': ("/nls → Balina hareketleri ve yoğunluk (NLS analizi)", None),
    'npr_handler.py': ("/npr → Nakit Piyasa Raporu", None),
    'eft_handler.py': ("/eft → ETF & ABD piyasaları", None),
    'ap_handler.py': ("/ap → Altların Güç Endeksi (AP)", "utils.ap_utils"),
    'price_handler.py': ("/p → Anlık fiyat, 24h değişim, hacim bilgisi", None),
    'p_handler.py': ("/p_ekle, /p_fav, /p_sil → Favori coin listesi yönetimi", None),
    'fr_handler.py': ("/fr → Funding Rate komutu ve günlük CSV kaydı", None),
    'whale_handler.py': ("/whale → Whale Alerts komutu ve günlük CSV kaydı", None),
    'binance_utils.py': ("Binance API'den veri çekme ve metrik fonksiyonlar", None),
    'csv_utils.py': ("CSV okuma/yazma ve Funding Rate, Whale CSV kayıt fonksiyonları", None),
    'trend_utils.py': ("Trend okları, yüzde değişim hesaplama ve formatlama", None),
    'fav_list.json': (None, None),
    'runtime.txt': (None, None),
    '.env': (None, None),
    '.gitignore': (None, None),
}


def format_tree(root_dir):
    tree_lines = []
    valid_files = []

    def walk(dir_path, prefix=""):
        items = sorted(os.listdir(dir_path))
        for i, item in enumerate(items):
            path = os.path.join(dir_path, item)
            connector = "└── " if i == len(items) - 1 else "├── "

            if os.path.isdir(path):
                if item.startswith("__") or (item.startswith(".") and item not in [".gitignore", ".env"]):
                    continue
                tree_lines.append(f"{prefix}{connector}{item}/")
                walk(path, prefix + ("    " if i == len(items) - 1 else "│   "))
            else:
                if item.startswith(".") and item not in [".env", ".gitignore"]:
                    continue
                ext = os.path.splitext(item)[1]
                if (ext not in EXT_LANG_MAP
                        and not item.endswith(('.txt', '.csv', '.json', '.md'))
                        and item not in [".env", ".gitignore"]):
                    continue
                desc, dep = FILE_INFO.get(item, (None, None))
                extra = f" # {desc}" if desc else ""
                extra += f" ♻️{dep}" if dep else ""
                tree_lines.append(f"{prefix}{connector}{item}{extra}")
                valid_files.append(path)

    walk(root_dir)
    return "\n".join(tree_lines), valid_files


def create_zip_with_tree_and_files(root_dir, zip_filename):
    tree_text, valid_files = format_tree(root_dir)
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("tree.txt", tree_text)
        for filepath in valid_files:
            arcname = os.path.relpath(filepath, root_dir)
            try:
                zipf.write(filepath, arcname)
            except Exception:
                pass
    return zip_filename


def scan_handlers_for_commands():
    commands = {}
    handler_dir = os.path.join(ROOT_DIR, "handlers")

    handler_pattern = re.compile(r'CommandHandler\(\s*["\'](\w+)["\']')
    var_handler_pattern = re.compile(r'CommandHandler\(\s*(\w+)')
    command_pattern = re.compile(r'COMMAND\s*=\s*["\'](\w+)["\']')

    # handlers/ içindeki tüm Python dosyalarını tarar(gizliler hariç)
    for fname in os.listdir(handler_dir):
        if not fname.endswith(".py") or fname.startswith("__"):
            continue
        fpath = os.path.join(handler_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            matches = handler_pattern.findall(content)
            for cmd in matches:
                desc = COMMAND_INFO.get(cmd.lower(), "(?)")
                commands[f"/{cmd}"] = f"{desc} ({fname})"
            matches_var = var_handler_pattern.findall(content)
            if "COMMAND" in matches_var:
                cmd_match = command_pattern.search(content)
                if cmd_match:
                    cmd = cmd_match.group(1)
                    desc = COMMAND_INFO.get(cmd.lower(), "(?)")
                    commands[f"/{cmd}"] = f"{desc} ({fname})"
        except Exception:
            continue
    return commands


@router.message(Command("dar"))
async def dar_command(message: Message, state: FSMContext):
    args = message.text.strip().split()[1:]
    mode = args[0].lower() if args else ""

    tree_text, valid_files = format_tree(ROOT_DIR)
    timestamp = datetime.now().strftime("%m%d_%H%M")

    if mode == "k":
        scanned = scan_handlers_for_commands()
        lines = [f"{cmd} → {desc}" for cmd, desc in sorted(scanned.items(), key=lambda x: x[0].lower())]
        text = "\n".join(lines) if lines else "Komut bulunamadı."
        await message.answer(f"<pre>{text}</pre>", parse_mode="HTML")
        return

    if mode == "t":
        txt_filename = f"{TELEGRAM_NAME}_{timestamp}.txt"
        try:
            with open(txt_filename, 'w', encoding='utf-8') as out:
                for filepath in valid_files:
                    rel_path = os.path.relpath(filepath, ROOT_DIR)
                    separator = "=" * (len(rel_path) + 4)
                    out.write(f"\n{separator}\n")
                    out.write(f"|| {rel_path} ||\n")
                    out.write(f"{separator}\n\n")
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            out.write(f.read())
                    except Exception as e:
                        out.write(f"<HATA: {e}>\n")
                    out.write("\n\n")
            await message.answer_document(FSInputFile(txt_filename))
        except Exception as e:
            await message.answer(f"Hata oluştu: {e}")
        finally:
            if os.path.exists(txt_filename):
                os.remove(txt_filename)
        return

    if mode.upper() == "Z":
        zip_filename = f"{TELEGRAM_NAME}_{timestamp}.zip"
        try:
            create_zip_with_tree_and_files(ROOT_DIR, zip_filename)
            await message.answer_document(FSInputFile(zip_filename))
        except Exception as e:
            await message.answer(f"Hata oluştu: {e}")
        finally:
            if os.path.exists(zip_filename):
                os.remove(zip_filename)
        return

    if len(tree_text) > TELEGRAM_MSG_LIMIT:
        txt_filename = f"{TELEGRAM_NAME}_{timestamp}.txt"
        try:
            with open(txt_filename, 'w', encoding='utf-8') as f:
                f.write(tree_text)
            await message.answer_document(FSInputFile(txt_filename))
        except Exception as e:
            await message.answer(f"Hata oluştu: {e}")
        finally:
            if os.path.exists(txt_filename):
                os.remove(txt_filename)
        return

    await message.answer(f"<pre>{tree_text}</pre>", parse_mode="HTML")
