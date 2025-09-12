#utils/smtp_client.py
import aiosmtplib
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class SMTPClient:
    """Async SMTP client with retry mechanism"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("MAIL_BEN")
        self.password = os.getenv("MAIL_PASSWORD")
        self.timeout = 30

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiosmtplib.SMTPException, TimeoutError)),
        reraise=True
    )
    async def send_email(self, to_email: str, subject: str, body: str, 
                        attachment_paths: Optional[List[str]] = None) -> bool:
        """Send email with attachments using SMTP with retry"""
        try:
            logger.info(f"📧 Sending email to: {to_email}, Subject: {subject}")
            
            # Email message oluştur
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Email body
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Attachments
            if attachment_paths:
                for attachment_path in attachment_paths:
                    if os.path.exists(attachment_path):
                        await self._add_attachment(msg, attachment_path)
                    else:
                        logger.warning(f"Attachment not found: {attachment_path}")
            
            # SMTP gönderimi
            async with aiosmtplib.SMTP(
                hostname=self.smtp_server, 
                port=self.smtp_port,
                timeout=self.timeout
            ) as smtp:
                await smtp.connect()
                await smtp.starttls()
                await smtp.login(self.username, self.password)
                await smtp.send_message(msg)
            
            logger.info(f"✅ Email sent successfully to: {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email send error to {to_email}: {e}")
            raise

    async def _add_attachment(self, msg: MIMEMultipart, attachment_path: str):
        """Dosya ekle"""
        try:
            async with aiofiles.open(attachment_path, 'rb') as f:
                file_data = await f.read()
            
            part = MIMEApplication(file_data, Name=os.path.basename(attachment_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)
            logger.debug(f"Added attachment: {attachment_path}")
            
        except Exception as e:
            logger.error(f"Attachment error {attachment_path}: {e}")
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
                await smtp.starttls()
                await smtp.login(self.username, self.password)
                await smtp.noop()
            
            logger.info("✅ SMTP connection test successful")
            return True
            
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
