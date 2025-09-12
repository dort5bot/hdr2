#utils/source_utils.py
import aiofiles
import logging
from typing import List, Set
from config import source_emails
import asyncio

logger = logging.getLogger(__name__)

class SourceManager:
    """Managed source email list with persistence"""
    
    def __init__(self):
        self.sources: Set[str] = set(source_emails)
        self._backup_file = "data/sources_backup.txt"

    async def add_source(self, email: str) -> bool:
        """Add source email async"""
        email = email.strip().lower()
        if email in self.sources:
            return False
        
        self.sources.add(email)
        await self._save_to_backup()
        logger.info(f"Source added: {email}")
        return True

    async def remove_source(self, email: str) -> bool:
        """Remove source email async"""
        email = email.strip().lower()
        if email not in self.sources:
            return False
        
        self.sources.remove(email)
        await self._save_to_backup()
        logger.info(f"Source removed: {email}")
        return True

    async def get_sources(self) -> List[str]:
        """Get all sources async"""
        return list(self.sources)

    async def contains_source(self, email: str) -> bool:
        """Check if email is in sources async"""
        return email.strip().lower() in self.sources

    async def _save_to_backup(self):
        """Save sources to backup file async"""
        try:
            async with aiofiles.open(self._backup_file, 'w') as f:
                for email in sorted(self.sources):
                    await f.write(f"{email}\n")
        except Exception as e:
            logger.error(f"Backup save error: {e}")

    async def load_from_backup(self):
        """Load sources from backup file async"""
        try:
            async with aiofiles.open(self._backup_file, 'r') as f:
                content = await f.read()
                self.sources = set(line.strip() for line in content.splitlines() if line.strip())
        except FileNotFoundError:
            logger.info("No backup file found, using default sources")
        except Exception as e:
            logger.error(f"Backup load error: {e}")

# Global instance
source_manager = SourceManager()

# Backward compatibility functions
async def add_source_email(email: str) -> bool:
    return await source_manager.add_source(email)

async def remove_source_email(email: str) -> bool:
    return await source_manager.remove_source(email)

async def get_source_emails() -> List[str]:
    return await source_manager.get_sources()

async def is_source_email(email: str) -> bool:
    return await source_manager.contains_source(email)
