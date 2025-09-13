# 2. Remote storage (ücretsiz alternatifler)
# - GitHub Gist (gruplar.json için)
# - MongoDB Atlas (ücretsiz 512MB)
# - Supabase (ücretsiz)
# - Google Drive API
import os
import json
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Dict, Any
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Render detection
IS_RENDER = os.getenv("RENDER", "false").lower() == "true"

# Dynamic base path - Render uyumlu
if IS_RENDER:
    BASE_DIR = Path("/tmp/telegram_bot")
else:
    BASE_DIR = Path(__file__).parent

# Directories
TEMP_DIR = BASE_DIR / "temp"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Create directories with Render compatibility
for directory in [TEMP_DIR, DATA_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

# Webhook/Polling seçimi
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
#WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "3000"))    ÇOK SAÇMALANMIŞ GEREKSİZ TANIMLAR EKLENMİŞ
WEBHOOK_PORT = int(os.getenv("PORT", "10000"))


# Scheduler ayarı
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is required")

MAIL_K1 = os.getenv("MAIL_K1")
MAIL_K2 = os.getenv("MAIL_K2")
MAIL_K3 = os.getenv("MAIL_K3")
MAIL_K4 = os.getenv("MAIL_K4")
MAIL_BEN = os.getenv("MAIL_BEN")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

# Admin IDs handling
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []
if ADMIN_IDS_STR:
    try:
        ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(",") if id.strip()]
    except ValueError as e:
        logger.warning(f"Invalid ADMIN_IDS format: {e}")

# Grup veri dosyası - Render uyumlu
GROUPS_FILE = DATA_DIR / "groups.json"
DB_FILE = DATA_DIR / "database.db"
SOURCES_BACKUP_FILE = DATA_DIR / "sources_backup.txt"

# Varsayılan gruplar
DEFAULT_GROUPS = [
    {"no": "GRUP_1", "name": "ANTALYA", "iller": "AFYON,AKSARAY,ANKARA,ANTALYA,BURDUR,ÇANKIRI,ISPARTA,KARAMAN,KAYSERI,KIRIKKALE,KIRŞEHIR,KONYA,UŞAK", "email": "dersdep@gmail.com"},
    {"no": "GRUP_2", "name": "MERSİN", "iller": "ADANA,ADIYAMAN,BATMAN,BINGÖL,BITLIS,DIYARBAKIR,ELAZIĞ,GAZIANTEP,HAKKARI,HATAY,KAHRAmanMARAS,KILIS,MALATYA,MARDIN,MERSIN,MUŞ,OSMANIYE,SIIRT,ŞANLIURFA,ŞIRNAK", "email": "dersdep@gmail.com"},
    {"no": "GRUP_3", "name": "İZMİR", "iller": "AFYON,AYDIN,BURDUR,ISPARTA,İZMIR,ÇANAKKALE,MANISA,MUĞLA,UŞAK", "email": "dersdep@gmail.com"},
    {"no": "GRUP_4", "name": "BURSA", "iller": "BALIKESIR,BURSA,ÇANAKKALE,DÜZCE,KOCAELI,SAKARYA,TEKIRDAĞ,YALOVA", "email": "GRUP_4@gmail.com"},
    {"no": "GRUP_5", "name": "BALIKESİR", "iller": "BALIKESIR,ÇANAKKALE", "email": "GRUP_5@gmail.com"},
    {"no": "GRUP_6", "name": "KARADENİZ", "iller": "ARTVIN,BAYBURT,ÇANKIRI,ERZINCAN,ERZURUM,GIRESUN,GÜMÜŞHANE,ORDU,RIZE,SAMSUN,SINOP,SIVAS,TOKAT,TRABZON", "email": "GRUP_6@gmail.com"},
    {"no": "GRUP_7", "name": "ERZİNCAN", "iller": "BINGÖL,ERZINCAN,ERZURUM,GIRESUN,GÜMÜŞHANE,KARS,ORDU,SIVAS,ŞIRNAK,TOKAT,TUNCELI", "email": "GRUP_7@gmail.com"},
    {"no": "GRUP_8", "name": "ESKİŞEHİR", "iller": "AFYON,ANKARA,BILECIK,ESKIŞEHIR,UŞAK", "email": "GRUP_8@gmail.com"},
    {"no": "GRUP_9", "name": "KÜTAHYA", "iller": "AFYON,ANKARA,BILECIK,BOZÜYÜK,BURSA,ESKIŞEHIR,KÜTAHYA,UŞAK", "email": "GRUP_9@gmail.com"},
    {"no": "GRUP_10", "name": "ÇORUM", "iller": "AMASYA,ANKARA,ÇANKIRI,ÇORUM,KASTAMONU,KAYSERI,KIRIKKALE,KIRŞEHIR,SAMSUN,TOKAT,YOZGAT", "email": "GRUP_10@gmail.com"},
    {"no": "GRUP_11", "name": "DENİZLİ", "iller": "AFYON,AYDIN,BURDUR,DENIZLI,ISPARTA,İZMIR,MANISA,MUĞLA,UŞAK", "email": "GRUP_11@gmail.com"},
    {"no": "GRUP_12", "name": "AKHİSAR", "iller": "MANISA", "email": "GRUP_12@gmail.com"},
    {"no": "GRUP_13", "name": "DÜZCE", "iller": "BOLU,DÜZCE,EDIRNE,İSTANBUL,KARABÜK,KIRKLARELI,KOCAELI,SAKARYA,TEKIRDAĞ,YALOVA,ZONGULDAK", "email": "GRUP_13@gmail.com"},
    {"no": "GRUP_14", "name": "TUNCAY", "iller": "AKSARAY,ANKARA,KAHRAmanMARAS,KIRIKKALE,KIRŞEHIR", "email": "GRUP_14@gmail.com"}
]

# Turkish city list
TURKISH_CITIES = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", 
    "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman", 
    "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", 
    "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", 
    "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", 
    "Hakkâri", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş", 
    "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kırıkkale", "Kırklareli", 
    "Kırşehir", "Kilis", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", 
    "Mardin", "Mersin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", 
    "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Şanlıurfa", "Şırnak", 
    "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", 
    "Zonguldak"
]

# IMAP ve SMTP ayarları
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# Data storage
source_emails = []
processed_mail_ids = set()

# Initialize data from environment
if MAIL_K1:
    source_emails.append(MAIL_K1)
if MAIL_K2:
    source_emails.append(MAIL_K2)
if MAIL_K3:
    source_emails.append(MAIL_K3)
if MAIL_K4:
    source_emails.append(MAIL_K4)

# Grupları yükle - Render uyumlu (environment backup)
def load_groups() -> List[Dict[str, Any]]:
    """Grupları JSON dosyasından veya environment'dan yükle"""
    
    # Önce environment'dan dene (Render için)
    groups_json_env = os.getenv("GROUPS_JSON")
    if groups_json_env:
        try:
            env_groups = json.loads(groups_json_env)
            logger.info("Gruplar environment'dan yüklendi")
            return convert_old_groups(env_groups)
        except json.JSONDecodeError as e:
            logger.warning(f"Environment GROUPS_JSON decode error: {e}")
    
    # Sonra dosyadan dene
    try:
        if GROUPS_FILE.exists():
            with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
                loaded_groups = json.load(f)
                logger.info("Gruplar dosyadan yüklendi")
                return convert_old_groups(loaded_groups)
        else:
            logger.info("groups.json dosyası oluşturuluyor...")
            save_groups(DEFAULT_GROUPS)
            logger.info(f"{len(DEFAULT_GROUPS)} varsayılan grup kaydedildi.")
            return DEFAULT_GROUPS
    except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
        logger.error(f"Groups file error: {e}, loading default groups")
        try:
            save_groups(DEFAULT_GROUPS)
        except Exception as save_error:
            logger.error(f"Backup save error: {save_error}")
        return DEFAULT_GROUPS

def convert_old_groups(old_groups: List[Dict]) -> List[Dict]:
    """Eski grup yapısını yeniye dönüştür"""
    new_groups = []
    for group in old_groups:
        new_group = group.copy()
        if "ad" in new_group and "name" not in new_group:
            new_group["name"] = new_group.pop("ad")
        new_groups.append(new_group)
    return new_groups

def save_groups(groups_data: List[Dict]):
    """Grupları JSON dosyasına kaydet ve environment'a backup al"""
    converted_groups = convert_old_groups(groups_data)
    
    # Dosyaya kaydet
    try:
        with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(converted_groups, f, ensure_ascii=False, indent=2)
        logger.info(f"Gruplar dosyaya kaydedildi: {GROUPS_FILE}")
    except Exception as e:
        logger.error(f"Gruplar dosyaya kaydedilemedi: {e}")
    
    # Environment backup için logla (manuel kopyalama için)
    groups_json_str = json.dumps(converted_groups, ensure_ascii=False)
    logger.info(f"Environment GROUPS_JSON backup (ilk 200 char): {groups_json_str[:200]}...")

# Grupları başlat
groups = load_groups()
logger.info(f"Loaded {len(groups)} groups")

# Prometheus metrics port
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))

# Application settings
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
PROCESS_TIMEOUT = int(os.getenv("PROCESS_TIMEOUT", "300"))  # 5 minutes
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))

# Render-specific optimizations
if IS_RENDER:
    logger.info("Render ortamında çalışıyor - /tmp dizini kullanılıyor")
    # SQLite için WAL mode (Render'da daha iyi performans)
    SQLITE_PRAGMAS = {
        'journal_mode': 'wal',
        'cache_size': -1000,  # KB cinsinden
        'foreign_keys': 1,
        'ignore_check_constraints': 0,
        'synchronous': 'normal'
    }
else:
    SQLITE_PRAGMAS = {
        'journal_mode': 'delete',
        'cache_size': -2000,
        'foreign_keys': 1,
        'ignore_check_constraints': 0,
        'synchronous': 'normal'
    }

# Version info
APP_VERSION = "2.0.0"
APP_NAME = "Telegram Mail Bot"
