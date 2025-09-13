#utils/gmail_client.py
import os
import imaplib
import email
import asyncio
import logging
import aiofiles
from email.header import decode_header
from typing import List, Tuple
from config import source_emails, TEMP_DIR, IMAP_SERVER, IMAP_PORT
from .file_utils import ensure_temp_dir

logger = logging.getLogger(__name__)

class GmailClient:
    """Async Gmail client with connection pooling"""
    
    def __init__(self):
        self.imap_server = IMAP_SERVER
        self.imap_port = IMAP_PORT
        self.username = os.getenv("MAIL_BEN")
        self.password = os.getenv("MAIL_PASSWORD")
        self.timeout = 30

    async def check_email(self) -> List[Tuple[str, str]]:
        """Check for new emails with Excel attachments asynchronously"""
        new_files = []
        
        try:
            # IMAP bağlantısını async yap
            mail = await self._connect_imap()
            if not mail:
                return new_files
            
            # Mail arama ve işleme
            status, messages = mail.search(None, 'UNSEEN')
            if status != "OK":
                await self._disconnect_imap(mail)
                return new_files
                
            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} unseen emails")
            
            # Her maili paralel işle
            tasks = []
            for email_id in email_ids:
                tasks.append(self._process_single_email(mail, email_id))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Sonuçları topla
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Email processing error: {result}")
                elif result:
                    new_files.extend(result)
            
            await self._disconnect_imap(mail)
            return new_files
            
        except Exception as e:
            logger.error(f"Email check error: {e}")
            return []

    async def _connect_imap(self):
        """IMAP bağlantısını async kur"""
        try:
            return await asyncio.to_thread(
                self._connect_imap_sync
            )
        except Exception as e:
            logger.error(f"IMAP connection error: {e}")
            return None

    def _connect_imap_sync(self):
        """Senkron IMAP bağlantısı"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.username, self.password)
            mail.select("inbox")
            return mail
        except Exception as e:
            logger.error(f"IMAP sync connection error: {e}")
            return None

    async def _disconnect_imap(self, mail):
        """IMAP bağlantısını async kapat"""
        try:
            await asyncio.to_thread(
                self._disconnect_imap_sync, mail
            )
        except Exception as e:
            logger.error(f"IMAP disconnect error: {e}")

    def _disconnect_imap_sync(self, mail):
        """Senkron IMAP bağlantı kapatma"""
        try:
            mail.close()
            mail.logout()
        except Exception:
            pass

    async def _process_single_email(self, mail, email_id) -> List[Tuple[str, str]]:
        """Tek bir email'i async işle"""
        try:
            status, msg_data = await asyncio.to_thread(
                mail.fetch, email_id, "(RFC822)"
            )
            
            if status != "OK":
                return []
            
            attachments = []
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    from_email = msg["From"]
                    
                    # Sadece kaynak mailleri işle
                    if not any(source in from_email for source in source_emails):
                        continue
                    
                    # Attachment'ları işle
                    email_attachments = await self._process_attachments(msg, from_email)
                    attachments.extend(email_attachments)
            
            return attachments
            
        except Exception as e:
            logger.error(f"Email {email_id} processing error: {e}")
            return []

    async def _process_attachments(self, msg, from_email) -> List[Tuple[str, str]]:
        """Attachment'ları async işle"""
        attachments = []
        
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
                
            filename = part.get_filename()
            if filename and any(filename.endswith(ext) for ext in ['.xlsx', '.xls']):
                try:
                    # Dosya adını decode et
                    filename_bytes, encoding = decode_header(filename)[0]
                    if isinstance(filename_bytes, bytes):
                        filename = filename_bytes.decode(encoding or 'utf-8')
                    
                    # Dosyayı kaydet
                    await ensure_temp_dir()
                    filepath = os.path.join(TEMP_DIR, filename)
                    
                    # Dosyayı async kaydet
                    file_data = part.get_payload(decode=True)
                    async with aiofiles.open(filepath, 'wb') as f:
                        await f.write(file_data)
                    
                    attachments.append((filepath, from_email))
                    logger.info(f"📎 New Excel file saved: {filename}")
                    
                except Exception as e:
                    logger.error(f"Attachment processing error: {e}")
        
        return attachments

    async def test_connection(self) -> bool:
        """Gmail bağlantı testi"""
        try:
            mail = await self._connect_imap()
            if mail:
                await self._disconnect_imap(mail)
                logger.info("✅ Gmail connection test successful")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Gmail connection test failed: {e}")
            return False

# Global instance
gmail_client = GmailClient()

# Backward compatibility functions
async def check_email() -> List[Tuple[str, str]]:
    """Backward compatible check function"""
    return await gmail_client.check_email()

async def test_gmail_connection() -> str:
    """Test connection wrapper"""
    success = await gmail_client.test_connection()
    return "✅ Gmail bağlantı testi başarılı" if success else "❌ Gmail bağlantı testi başarısız"
