#utils/gmail_client.py
#attachment için (dosya_yolu, gönderen_email, email_konusu) şeklinde 3'lü tuple dönecek
import os
import imaplib
import email
import asyncio
import logging
import aiofiles
from email.header import decode_header
from email.utils import parseaddr
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

        # Gerekli çevre değişkenleri kontrolü
        if not self.username or not self.password:
            logger.error("❌ Email credentials are missing. Please set MAIL_BEN and MAIL_PASSWORD in your environment.")
    
    async def check_email(self) -> List[Tuple[str, str, str]]:
        """Check for new emails with Excel attachments asynchronously"""
        new_files = []
        
        try:
            mail = await self._connect_imap()
            if not mail:
                return new_files
            
            status, messages = mail.search(None, 'UNSEEN')
            if status != "OK":
                await self._disconnect_imap(mail)
                return new_files
                
            email_ids = messages[0].split()
            logger.info(f"📨 Found {len(email_ids)} unseen emails")
            
            # Her maili sırayla işle (IMAP thread-safe değil)
            for email_id in email_ids:
                result = await self._process_single_email(mail, email_id)
                if result:
                    new_files.extend(result)
            
            await self._disconnect_imap(mail)
            return new_files
            
        except Exception as e:
            logger.error(f"❌ Email check error: {e}")
            return []

    async def _connect_imap(self):
        """IMAP bağlantısını async kur"""
        try:
            return await asyncio.to_thread(
                self._connect_imap_sync
            )
        except Exception as e:
            logger.error(f"❌ IMAP connection error: {e}")
            return None

    def _connect_imap_sync(self):
        """Senkron IMAP bağlantısı"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.username, self.password)
            mail.select("inbox")
            return mail
        except Exception as e:
            logger.error(f"❌ IMAP sync connection error: {e}")
            return None

    async def _disconnect_imap(self, mail):
        """IMAP bağlantısını async kapat"""
        try:
            await asyncio.to_thread(
                self._disconnect_imap_sync, mail
            )
        except Exception as e:
            logger.error(f"❌ IMAP disconnect error: {e}")

    def _disconnect_imap_sync(self, mail):
        """Senkron IMAP bağlantı kapatma"""
        try:
            mail.close()
            mail.logout()
        except Exception:
            pass

    async def _process_single_email(self, mail, email_id) -> List[Tuple[str, str, str]]:
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
                    
                    # Doğru adresi çek
                    from_email = parseaddr(msg["From"])[1]
                    subject = self._decode_header(msg["Subject"] or "No Subject")
                    
                    if not any(source in from_email for source in source_emails):
                        continue
                    
                    # Attachment'ları işle
                    email_attachments = await self._process_attachments(msg, from_email, subject)
                    attachments.extend(email_attachments)
            
            return attachments
            
        except Exception as e:
            logger.error(f"❌ Email {email_id} processing error: {e}")
            return []

    def _decode_header(self, header):
        """Email header'ını decode et"""
        if not header:
            return "No Subject"
        
        try:
            decoded_parts = decode_header(header)
            decoded_str = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    decoded_str += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    decoded_str += str(part)
            return decoded_str
        except Exception:
            return header

    async def _process_attachments(self, msg, from_email, subject) -> List[Tuple[str, str, str]]:
        """Attachment'ları async işle"""
        attachments = []
        
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            content_type = part.get_content_type()
            
            # MIME tipi kontrolü (yalnızca Excel dosyaları)
            allowed_mime_types = [
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-excel'
            ]
            if filename and any(filename.endswith(ext) for ext in ['.xlsx', '.xls']) and content_type in allowed_mime_types:
                try:
                    # Dosya adını decode et
                    filename_bytes, encoding = decode_header(filename)[0]
                    if isinstance(filename_bytes, bytes):
                        filename = filename_bytes.decode(encoding or 'utf-8')
                    
                    # Dosyayı kaydet
                    await ensure_temp_dir()
                    filepath = os.path.join(TEMP_DIR, filename)
                    
                    file_data = part.get_payload(decode=True)
                    async with aiofiles.open(filepath, 'wb') as f:
                        await f.write(file_data)
                    
                    attachments.append((filepath, from_email, subject))
                    logger.info(f"📎 Saved attachment from {from_email} (Subject: {subject}): {filename} → {filepath}")
                    
                except Exception as e:
                    logger.error(f"❌ Attachment processing error: {e}")
            else:
                logger.info(f"⏭️ Skipped non-excel attachment or unsupported MIME: {filename}, type={content_type}")
        
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
async def check_email() -> List[Tuple[str, str, str]]:
    """Backward compatible check function"""
    return await gmail_client.check_email()

async def test_gmail_connection() -> str:
    """Test connection wrapper"""
    success = await gmail_client.test_connection()
    return "✅ Gmail bağlantı testi başarılı" if success else "❌ Gmail bağlantı testi başarısız"
