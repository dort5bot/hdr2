# data/group_manager.py
# Grup Yönetim Scripti JSON
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
                    return json.load(f)
            else:
                self.save_groups(DEFAULT_GROUPS)
                return DEFAULT_GROUPS
        except Exception as e:
            logger.error(f"Load groups error: {e}")
            return DEFAULT_GROUPS

    def save_groups(self, groups_data: List[Dict[str, Any]]):
        """Grupları kaydet"""
        try:
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

    def get_cities_for_group(self, group_no: str) -> List[str]:
        """Grup için şehir listesi getir"""
        group = self.get_group_by_no(group_no)
        if group and 'iller' in group:
            return [city.strip() for city in group['iller'].split(',')]
        return []

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
            # Grup numarası kontrolü
            if self.get_group_by_no(group_data['no']):
                logger.warning(f"Group {group_data['no']} already exists")
                return False
            
            self.groups.append(group_data)
            self.save_groups(self.groups)
            logger.info(f"Group added: {group_data['no']} - {group_data['name']}")
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
                    logger.info(f"Group deleted: {group_no} - {deleted_group['name']}")
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

def add_new_group(group_data: Dict[str, Any]) -> bool:
    return group_manager.add_group(group_data)

def update_existing_group(group_no: str, updated_data: Dict[str, Any]) -> bool:
    return group_manager.update_group(group_no, updated_data)

def delete_existing_group(group_no: str) -> bool:
    return group_manager.delete_group(group_no)
