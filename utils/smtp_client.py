#utils/smtp_client.py, mail gönderme
import aiosmtplib
import logging
import os
import aiofiles
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import Header
from typing import Optional, List, Union
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class SMTPClient:
    """Async SMTP client with retry mechanism and attachment support"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("MAIL_BEN")
        self.password = os.getenv("MAIL_PASSWORD")
        self.timeout = 30
        self.connection_pool = None
        
        # Gelişmiş doğrulama
        if not all([self.smtp_server, self.smtp_port, self.username, self.password]):
            missing = []
            if not self.smtp_server: missing.append("SMTP_SERVER")
            if not self.smtp_port: missing.append("SMTP_PORT")
            if not self.username: missing.append("MAIL_BEN")
            if not self.password: missing.append("MAIL_PASSWORD")
            
            logger.error(f"❌ Eksik SMTP konfigürasyonu: {', '.join(missing)}")
            raise ValueError(f"Eksik SMTP konfigürasyonu: {', '.join(missing)}")
        
        # E-posta adresi doğrulama
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if self.username and not re.match(email_regex, self.username):
            logger.warning("⚠️ Geçersiz e-posta formatı: MAIL_BEN")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiosmtplib.SMTPException, TimeoutError, ConnectionError)),
        reraise=True
    )
    async def send_email(self, to_email: Union[str, List[str]], subject: str, body: str, 
                         attachment_paths: Optional[List[str]] = None,
                         cc_emails: Optional[Union[str, List[str]]] = None,
                         bcc_emails: Optional[Union[str, List[str]]] = None,
                         html: bool = False) -> bool:
        """Send email with attachments using SMTP with retry"""
        try:
            # Alıcı listesini düzelt
            if isinstance(to_email, str):
                to_email = [to_email]
            
            logger.info(f"📧 Sending email → To: {', '.join(to_email)}, Subject: {subject}")
            
            # Create message
            msg = await self.create_message(
                to_email, subject, body, attachment_paths, cc_emails, bcc_emails, html
            )
            
            # SMTP gönderimi
            async with aiosmtplib.SMTP(
                hostname=self.smtp_server, 
                port=self.smtp_port,
                timeout=self.timeout
            ) as smtp:
                await smtp.connect()
                if self.smtp_port == 587:  # STARTTLS için port kontrolü
                    await smtp.starttls()
                await smtp.login(self.username, self.password)
                await smtp.send_message(msg)
            
            logger.info(f"✅ Email sent successfully to: {', '.join(to_email)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email send error to {to_email}: {e}")
            raise

    async def create_message(self, to_email: List[str], subject: str, body: str, 
                             attachment_paths: Optional[List[str]] = None,
                             cc_emails: Optional[Union[str, List[str]]] = None,
                             bcc_emails: Optional[Union[str, List[str]]] = None,
                             html: bool = False) -> MIMEMultipart:
        """E-posta mesajını hazırla (gönderim yapmaz)"""
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = ', '.join(to_email)
        msg['Subject'] = Header(subject, 'utf-8').encode()

        # CC ve BCC ekle
        if cc_emails:
            if isinstance(cc_emails, str):
                cc_emails = [cc_emails]
            msg['Cc'] = ', '.join(cc_emails)
        
        # BCC header'da gösterilmez, gönderim sırasında eklenir
        all_recipients = to_email.copy()
        if cc_emails:
            all_recipients.extend(cc_emails)
        if bcc_emails:
            if isinstance(bcc_emails, str):
                bcc_emails = [bcc_emails]
            all_recipients.extend(bcc_emails)

        # Body ekle (HTML veya plain text)
        content_type = 'html' if html else 'plain'
        msg.attach(MIMEText(body, content_type, 'utf-8'))
        
        # Attachments ekle
        if attachment_paths:
            for attachment_path in attachment_paths:
                if os.path.exists(attachment_path):
                    await self._add_attachment(msg, attachment_path)
                else:
                    logger.warning(f"⚠️ Attachment not found: {attachment_path}")
        
        return msg

    async def send_prepared_message(self, msg: MIMEMultipart, 
                                  bcc_emails: Optional[Union[str, List[str]]] = None) -> bool:
        """Hazır bir MIMEMultipart mesajını gönder"""
        try:
            # BCC alıcılarını ekle
            all_recipients = []
            if msg['To']:
                all_recipients.extend([addr.strip() for addr in msg['To'].split(',')])
            if msg['Cc']:
                all_recipients.extend([addr.strip() for addr in msg['Cc'].split(',')])
            if bcc_emails:
                if isinstance(bcc_emails, str):
                    bcc_emails = [bcc_emails]
                all_recipients.extend(bcc_emails)
            
            async with aiosmtplib.SMTP(
                hostname=self.smtp_server, 
                port=self.smtp_port,
                timeout=self.timeout
            ) as smtp:
                await smtp.connect()
                if self.smtp_port == 587:
                    await smtp.starttls()
                await smtp.login(self.username, self.password)
                await smtp.send_message(msg, to=all_recipients)
            
            logger.info("✅ Prepared message sent successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error sending prepared message: {e}")
            return False

    async def _add_attachment(self, msg: MIMEMultipart, attachment_path: str):
        """Dosya ekle"""
        try:
            MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024  # 25MB
            
            size = os.path.getsize(attachment_path)
            if size > MAX_ATTACHMENT_SIZE:
                logger.error(f"❌ Ek boyutu çok büyük: {size} bytes (max: {MAX_ATTACHMENT_SIZE})")
                raise ValueError("Ek boyutu sınırı aşıyor")
            
            logger.debug(f"📎 Adding attachment: {attachment_path} ({size/1024:.1f} KB)")
            
            async with aiofiles.open(attachment_path, 'rb') as f:
                file_data = await f.read()
            
            part = MIMEApplication(file_data, Name=os.path.basename(attachment_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)
            logger.info(f"✅ Attachment added: {attachment_path}")
            
        except Exception as e:
            logger.error(f"❌ Attachment error {attachment_path}: {e}")
            raise

    async def test_connection(self) -> bool:
        """SMTP bağlantı testi"""
        try:
            async with aiosmtplib.SMTP(
                hostname=self.smtp_server, 
                port=self.smtp_port,
                timeout=10
            ) as smtp:
                await smtp.connect()
                # STARTTLS desteğini kontrol et
                if self.smtp_port == 587:
                    await smtp.starttls()
                await smtp.login(self.username, self.password)
                await smtp.noop()
            
            logger.info("✅ SMTP connection test successful")
            return True
            
        except aiosmtplib.SMTPAuthenticationError:
            logger.error("❌ SMTP kimlik doğrulama hatası")
            return False
        except aiosmtplib.SMTPConnectError:
            logger.error("❌ SMTP bağlantı hatası")
            return False
        except Exception as e:
            logger.error(f"❌ SMTP connection test failed: {e}")
            return False


# Global instance
smtp_client = SMTPClient()

# Backward compatibility functions
async def send_email_with_smtp(to_email: str, subject: str, body: str, 
                               attachment_path: Optional[str] = None) -> bool:
    """Backward compatible send function"""
    attachment_paths = [attachment_path] if attachment_path else None
    return await smtp_client.send_email(to_email, subject, body, attachment_paths)

async def test_smtp_connection() -> str:
    """Test connection wrapper"""
    success = await smtp_client.test_connection()
    return "✅ SMTP bağlantı testi başarılı" if success else "❌ SMTP bağlantı testi başarısız"
    
