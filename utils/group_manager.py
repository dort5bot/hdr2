#db_manager.py
#data/db_manager.py  → → → utils/group_manager.py
# İçerik AYNI kalacak, sadece dosya adı ve yeri değişecek
# Grup yönetimi burada  (JSON grup yönetimi)

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
            # Grup numarası benzersiz olmalı
            if self.get_group_by_no(group_data['no']):
                logger.warning(f"Group already exists: {group_data['no']}")
                return False
            
            self.groups.append(group_data)
            self.save_groups(self.groups)
            return True
        except Exception as e:
            logger.error(f"Add group error: {e}")
            return False

    def remove_group(self, group_no: str) -> bool:
        """Grup sil"""
        try:
            original_count = len(self.groups)
            self.groups = [g for g in self.groups if g['no'] != group_no]
            
            if len(self.groups) < original_count:
                self.save_groups(self.groups)
                return True
            return False
        except Exception as e:
            logger.error(f"Remove group error: {e}")
            return False

    def update_group(self, group_no: str, updated_data: Dict[str, Any]) -> bool:
        """Grup güncelle"""
        try:
            for i, group in enumerate(self.groups):
                if group['no'] == group_no:
                    self.groups[i] = {**group, **updated_data}
                    self.save_groups(self.groups)
                    return True
            return False
        except Exception as e:
            logger.error(f"Update group error: {e}")
            return False
            
    # İsterseniz daha fazla özellik ekleyebilirsiniz:
    def get_all_cities(self) -> List[str]:
        """Tüm gruplardaki tüm şehirleri listeler"""
        all_cities = []
        for group in self.groups:
            all_cities.extend(self.get_cities_for_group(group['no']))
        return sorted(set(all_cities))
    
    def validate_city(self, city_name: str) -> bool:
        """Şehrin herhangi bir grupta olup olmadığını kontrol eder"""
        return self.find_group_for_city(city_name) is not None


# Global instance
group_manager = GroupManager()
