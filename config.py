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

# Webhook/Polling seçimi
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "3000"))

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

# Grup veri dosyası
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
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

# Temp directory
TEMP_DIR = Path(os.getcwd()) / "temp"
TEMP_DIR.mkdir(exist_ok=True, parents=True)

# Logs directory
LOGS_DIR = Path(os.getcwd()) / "logs"
LOGS_DIR.mkdir(exist_ok=True, parents=True)

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

# Grupları yükle
def load_groups() -> List[Dict[str, Any]]:
    """Grupları JSON dosyasından yükle"""
    try:
        if GROUPS_FILE.exists():
            with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
                loaded_groups = json.load(f)
                return convert_old_groups(loaded_groups)
        else:
            logger.info("groups.json dosyası oluşturuluyor...")
            save_groups(DEFAULT_GROUPS)
            logger.info(f"{len(DEFAULT_GROUPS)} grup kaydedildi.")
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
    """Grupları JSON dosyasına kaydet"""
    converted_groups = convert_old_groups(groups_data)
    with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(converted_groups, f, ensure_ascii=False, indent=2)

# Grupları başlat
groups = load_groups()
logger.info(f"Loaded {len(groups)} groups from {GROUPS_FILE}")

# Prometheus metrics port
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))

# Application settings
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
PROCESS_TIMEOUT = int(os.getenv("PROCESS_TIMEOUT", "300"))  # 5 minutes
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
