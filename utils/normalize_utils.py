#utils/normalize_utils.py
import re
import pandas as pd
from typing import Optional

def normalize_text(text) -> str:
    """Metni normalize et: büyük harf, Türkçe karakter düzeltme"""
    if pd.isna(text):
        return ""
    
    text_str = str(text).strip().upper()
    
    turkish_chars = {
        'İ': 'I', 'Ğ': 'G', 'Ü': 'U', 'Ş': 'S', 'Ö': 'O', 'Ç': 'C',
        'ı': 'I', 'ğ': 'G', 'ü': 'U', 'ş': 'S', 'ö': 'O', 'ç': 'C'
    }
    
    for old, new in turkish_chars.items():
        text_str = text_str.replace(old, new)
    
    text_str = re.sub(r'\s+', ' ', text_str).strip()
    return text_str

def normalize_city_name(city_name: str) -> Optional[str]:
    """Şehir ismini normalize et"""
    if not city_name:
        return None
    
    normalized = normalize_text(city_name)
    
    # Özel durumlar
    special_cases = {
        'ISTANBUL': 'İSTANBUL',
        'IZMIR': 'İZMİR',
        'IZMIT': 'İZMİT',
        'KOCAELI': 'KOCAELİ',
        'CANAKKALE': 'ÇANAKKALE',
        'CORUM': 'ÇORUM',
        'GUMUSHANE': 'GÜMÜŞHANE',
        'SANLIURFA': 'ŞANLIURFA',
        'SIRNAK': 'ŞIRNAK',
        'KIRIKKALE': 'KIRIKKALE',
        'KIRKLARELI': 'KIRKLARELİ',
        'KIRSEHIR': 'KIRŞEHIR',
        'KARABUK': 'KARABÜK',
        'BINGOL': 'BİNGÖL',
        'BATMAN': 'BATMAN',
        'HAKKARI': 'HAKKARİ',
        'VAN': 'VAN',
        'MUS': 'MUŞ',
        'SIIRT': 'SİİRT',
        'DIYARBAKIR': 'DİYARBAKIR'
    }
    
    return special_cases.get(normalized, normalized)

def is_valid_city(city_name: str) -> bool:
    """Geçerli bir şehir ismi mi kontrol et"""
    from config import TURKISH_CITIES
    normalized_city = normalize_city_name(city_name)
    return normalized_city in [normalize_city_name(city) for city in TURKISH_CITIES]
