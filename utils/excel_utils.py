#utils/excel_utils.py
import pandas as pd
import datetime
import os
import logging
import re
import asyncio
from typing import Dict, List, Optional
from pathlib import Path
from config import TURKISH_CITIES, groups, TEMP_DIR
from .normalize_utils import normalize_text

logger = logging.getLogger(__name__)

async def process_excel_files() -> Dict[str, List[str]]:
    """Process all Excel files in temp directory and group by cities asynchronously"""
    results = {}
    
    try:
        # Temp dizinindeki Excel dosyalarını bul
        excel_files = [f for f in os.listdir(TEMP_DIR) 
                      if f.lower().endswith(('.xlsx', '.xls'))]
        
        if not excel_files:
            logger.info("No Excel files found in temp directory")
            return results
        
        # Paralel işleme için task'lar oluştur
        tasks = []
        for filename in excel_files:
            filepath = os.path.join(TEMP_DIR, filename)
            tasks.append(process_single_excel(filepath, filename, results))
        
        # Tüm Excel dosyalarını paralel işle
        await asyncio.gather(*tasks)
        
        logger.info(f"Processed {len(excel_files)} Excel files, found {len(results)} groups")
        return results
        
    except Exception as e:
        logger.error(f"Excel processing error: {e}")
        return {}

async def process_single_excel(filepath: str, filename: str, results: Dict[str, List[str]]):
    """Tek bir Excel dosyasını async işle"""
    try:
        # Excel'i async olarak oku
        df = await read_excel_async(filepath)
        if df is None or df.empty:
            return
        
        # Şehir sütununu bul
        city_column = await find_city_column_async(df, filename)
        if not city_column:
            logger.warning(f"No city column found in {filename}")
            return
        
        # Satırları işle
        await process_rows_async(df, city_column, results, filename)
        
    except Exception as e:
        logger.error(f"Error processing {filename}: {e}")

async def read_excel_async(filepath: str) -> Optional[pd.DataFrame]:
    """Excel'i async olarak oku"""
    try:
        return await asyncio.to_thread(pd.read_excel, filepath)
    except Exception as e:
        logger.error(f"Error reading Excel {filepath}: {e}")
        return None

async def find_city_column_async(df: pd.DataFrame, filename: str) -> Optional[str]:
    """Şehir sütununu async bul"""
    return await asyncio.to_thread(find_city_column, df, filename)

def find_city_column(df: pd.DataFrame, filename: str) -> Optional[str]:
    """Şehir sütununu senkron bul"""
    try:
        for col in df.columns:
            col_normalized = normalize_text(col)
            
            city_keywords = ['SEHIR', 'CITY', 'IL', 'LOCATION', 'CITY_NAME', 
                           'ILLER', 'PROVINCE', 'SEHIRLER', 'ILCE', 'DISTRICT', 'YER']
            if any(keyword in col_normalized for keyword in city_keywords):
                return col
            
            if any(normalize_text(city) in col_normalized for city in TURKISH_CITIES):
                return col
        
        # İlk 20 satırda şehir ismi ara
        for col in df.columns:
            try:
                city_count = 0
                for i in range(min(20, len(df))):
                    cell_value = str(df.iloc[i][col]) if pd.notna(df.iloc[i][col]) else ""
                    cell_normalized = normalize_text(cell_value)
                    
                    for city in TURKISH_CITIES:
                        city_normalized = normalize_text(city)
                        if city_normalized and city_normalized in cell_normalized:
                            city_count += 1
                            if city_count >= 3:
                                return col
                            break
            except Exception:
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"City column finding error in {filename}: {e}")
        return None

async def process_rows_async(df: pd.DataFrame, city_column: str, 
                           results: Dict[str, List[str]], filename: str):
    """Satırları async işle"""
    await asyncio.to_thread(process_rows, df, city_column, results, filename)

def process_rows(df: pd.DataFrame, city_column: str, 
                results: Dict[str, List[str]], filename: str):
    """Satırları senkron işle"""
    try:
        processed_count = 0
        for index, row in df.iterrows():
            city = row[city_column] if pd.notna(row[city_column]) else ""
            if not city:
                continue
                
            city_str = normalize_text(city)
            
            for group in groups:
                group_iller = [normalize_text(il.strip()) for il in group["iller"].split(",")]
                
                for il in group_iller:
                    if il == city_str:
                        if group["no"] not in results:
                            results[group["no"]] = []
                        if filename not in results[group["no"]]:
                            results[group["no"]].append(filename)
                        processed_count += 1
                        break
        
        logger.info(f"Processed {processed_count} rows from {filename}")
        
    except Exception as e:
        logger.error(f"Row processing error in {filename}: {e}")

async def create_group_excel(group_no: str, filepaths: List[str]) -> Optional[str]:
    """Basit ve garantili Excel oluşturma - Async versiyon"""
    try:
        logger.info(f"🔄 Creating group Excel: {group_no}")
        
        if not filepaths:
            logger.error("❌ Empty file list")
            return None
        
        # Tüm dosyaları async oku
        all_dfs = []
        for filepath in filepaths:
            full_path = os.path.join(TEMP_DIR, filepath)
            if not os.path.exists(full_path):
                logger.error(f"❌ File not found: {full_path}")
                continue
                
            try:
                df = await read_excel_async(full_path)
                if df is not None:
                    all_dfs.append(df)
                    logger.info(f"✅ {filepath} read: {len(df)} rows")
            except Exception as e:
                logger.error(f"❌ {filepath} read error: {e}")
                continue
        
        if not all_dfs:
            logger.error("❌ No files could be read")
            return None
        
        # DataFrameleri birleştir
        try:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            logger.info(f"✅ {len(all_dfs)} files merged: {len(combined_df)} rows")
        except Exception as e:
            logger.error(f"❌ DataFrame merge error: {e}")
            return None
        
        # Çıktı dosyasını oluştur
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        output_filename = f"{group_no}_{timestamp}.xlsx"
        output_path = os.path.join(TEMP_DIR, output_filename)
        
        # Excel'i async kaydet
        try:
            await save_excel_async(combined_df, output_path)
            logger.info(f"✅ Excel saved: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"❌ Excel save error: {e}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return None

async def save_excel_async(df: pd.DataFrame, output_path: str):
    """Excel'i async olarak kaydet"""
    await asyncio.to_thread(df.to_excel, output_path, index=False, engine='openpyxl')

async def validate_excel_file(filepath: str) -> bool:
    """Excel dosyasını doğrula"""
    try:
        df = await read_excel_async(filepath)
        return df is not None and not df.empty
    except Exception:
        return False
