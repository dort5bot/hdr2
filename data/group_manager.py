# data/group_manager.py
# Grup Yönetim Scripti JSON hazırlar
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import GROUPS_FILE, DEFAULT_GROUPS

logger = logging.getLogger(__name__)

class GroupManager:
    """Grup yöneticisi - JSON tabanlı grup yönetimi"""
    
    def __init__(self, groups_file: Path = GROUPS_FILE):
        self.groups_file = groups_file
        self.groups = self.load_groups()

    def load_groups(self) -> List[Dict[str, Any]]:
        """Grupları yükle"""
        try:
            if self.groups_file.exists():
                with open(self.groups_file, 'r', encoding='utf-8') as f:
                    groups_data = json.load(f)
                    
                    # Eski formatı yeni formata dönüştür (geriye uyumluluk)
                    for group in groups_data:
                        if 'email' not in group:
                            group['email'] = f"grup{group['no']}@firma.com"
                            logger.warning(f"Eski format: {group['no']} grubuna varsayılan email eklendi")
                    
                    return groups_data
            else:
                self.save_groups(DEFAULT_GROUPS)
                return DEFAULT_GROUPS
        except Exception as e:
            logger.error(f"Load groups error: {e}")
            return DEFAULT_GROUPS

    def save_groups(self, groups_data: List[Dict[str, Any]]):
        """Grupları kaydet"""
        try:
            # Email alanlarını kontrol et
            for group in groups_data:
                if 'email' not in group or not group['email']:
                    group['email'] = f"grup{group['no']}@firma.com"
                    logger.warning(f"Eksik email: {group['no']} grubuna varsayılan email eklendi")
            
            with open(self.groups_file, 'w', encoding='utf-8') as f:
                json.dump(groups_data, f, ensure_ascii=False, indent=2)
            self.groups = groups_data
            logger.info(f"Groups saved successfully: {len(groups_data)} groups")
        except Exception as e:
            logger.error(f"Save groups error: {e}")

    def get_group_by_no(self, group_no: str) -> Optional[Dict[str, Any]]:
        """Grup numarasına göre grup bul"""
        for group in self.groups:
            if group['no'] == group_no:
                return group
        return None

    def get_group_by_name(self, group_name: str) -> Optional[Dict[str, Any]]:
        """Grup ismine göre grup bul"""
        for group in self.groups:
            if group['name'].lower() == group_name.lower():
                return group
        return None

    def get_group_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Email adresine göre grup bul"""
        for group in self.groups:
            if group.get('email', '').lower() == email.lower():
                return group
        return None

    def get_cities_for_group(self, group_no: str) -> List[str]:
        """Grup için şehir listesi getir"""
        group = self.get_group_by_no(group_no)
        if group and 'iller' in group:
            return [city.strip() for city in group['iller'].split(',')]
        return []

    def get_email_for_group(self, group_no: str) -> Optional[str]:
        """Grup numarasına göre email adresi getir"""
        group = self.get_group_by_no(group_no)
        return group.get('email') if group else None

    def find_group_for_city(self, city_name: str) -> Optional[Dict[str, Any]]:
        """Şehir için uygun grup bul"""
        normalized_city = city_name.upper().strip()
        for group in self.groups:
            cities = self.get_cities_for_group(group['no'])
            if normalized_city in cities:
                return group
        return None

    def add_group(self, group_data: Dict[str, Any]) -> bool:
        """Yeni grup ekle"""
        try:
            # Zorunlu alanları kontrol et
            required_fields = ['no', 'name', 'email', 'iller']
            for field in required_fields:
                if field not in group_data:
                    logger.error(f"Eksik alan: {field}")
                    return False
            
            # Grup numarası kontrolü
            if self.get_group_by_no(group_data['no']):
                logger.warning(f"Group {group_data['no']} already exists")
                return False
            
            self.groups.append(group_data)
            self.save_groups(self.groups)
            logger.info(f"Group added: {group_data['no']} - {group_data['name']} - {group_data['email']}")
            return True
        except Exception as e:
            logger.error(f"Add group error: {e}")
            return False

    def update_group(self, group_no: str, updated_data: Dict[str, Any]) -> bool:
        """Grubu güncelle"""
        try:
            for i, group in enumerate(self.groups):
                if group['no'] == group_no:
                    self.groups[i] = {**group, **updated_data}
                    self.save_groups(self.groups)
                    logger.info(f"Group updated: {group_no}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Update group error: {e}")
            return False

    def delete_group(self, group_no: str) -> bool:
        """Grubu sil"""
        try:
            for i, group in enumerate(self.groups):
                if group['no'] == group_no:
                    deleted_group = self.groups.pop(i)
                    self.save_groups(self.groups)
                    logger.info(f"Group deleted: {group_no} - {deleted_group['name']} - {deleted_group.get('email', 'N/A')}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Delete group error: {e}")
            return False

    def get_all_groups(self) -> List[Dict[str, Any]]:
        """Tüm grupları getir"""
        return self.groups

    def get_groups_count(self) -> int:
        """Toplam grup sayısını getir"""
        return len(self.groups)

    def get_emails_list(self) -> List[str]:
        """Tüm grup email adreslerini listele"""
        return [group.get('email', '') for group in self.groups if group.get('email')]

    def get_cities_count(self) -> int:
        """Toplam şehir sayısını getir"""
        count = 0
        for group in self.groups:
            cities = self.get_cities_for_group(group['no'])
            count += len(cities)
        return count

    def export_groups_to_json(self, export_path: Path) -> bool:
        """Grupları JSON olarak dışa aktar"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.groups, f, ensure_ascii=False, indent=2)
            logger.info(f"Groups exported to: {export_path}")
            return True
        except Exception as e:
            logger.error(f"Export groups error: {e}")
            return False

    def import_groups_from_json(self, import_path: Path) -> bool:
        """Grupları JSON'dan içe aktar"""
        try:
            if not import_path.exists():
                logger.error(f"Import file not found: {import_path}")
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_groups = json.load(f)
            
            # Basit doğrulama
            if not isinstance(imported_groups, list):
                logger.error("Invalid import format: expected list of groups")
                return False
            
            for group in imported_groups:
                if 'no' not in group or 'name' not in group:
                    logger.error("Invalid group format: missing required fields")
                    return False
                
                # Email yoksa varsayılan ekle
                if 'email' not in group or not group['email']:
                    group['email'] = f"grup{group['no']}@firma.com"
            
            self.save_groups(imported_groups)
            logger.info(f"Groups imported from: {import_path}")
            return True
        except Exception as e:
            logger.error(f"Import groups error: {e}")
            return False

# Global instance
group_manager = GroupManager()

# Yardımcı fonksiyonlar
def get_group_for_city(city_name: str) -> Optional[Dict[str, Any]]:
    return group_manager.find_group_for_city(city_name)

def get_all_groups() -> List[Dict[str, Any]]:
    return group_manager.get_all_groups()

def get_group_info(group_no: str) -> Optional[Dict[str, Any]]:
    return group_manager.get_group_by_no(group_no)

def get_group_email(group_no: str) -> Optional[str]:
    return group_manager.get_email_for_group(group_no)

def get_group_by_email(email: str) -> Optional[Dict[str, Any]]:
    return group_manager.get_group_by_email(email)

def add_new_group(group_data: Dict[str, Any]) -> bool:
    return group_manager.add_group(group_data)

def update_existing_group(group_no: str, updated_data: Dict[str, Any]) -> bool:
    return group_manager.update_group(group_no, updated_data)

def delete_existing_group(group_no: str) -> bool:
    return group_manager.delete_group(group_no)

def get_all_group_emails() -> List[str]:
    return group_manager.get_emails_list()
