"""
Email Service for sending verification codes
Supports: Mock (console), SMTP (Gmail/others), SendGrid, AWS SES
"""

import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending verification codes"""
    
    def __init__(self, mode: str = "mock"):
        """
        Initialize email service
        
        Args:
            mode: "mock" (console), "sendgrid", "aws_ses", "smtp"
        """
        self.mode = mode
        
        # SMTP configuration from environment variables
        if mode == "smtp":
            self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
            self.smtp_user = os.getenv("SMTP_USER", "")
            self.smtp_password = os.getenv("SMTP_PASSWORD", "")
            self.smtp_from_email = os.getenv("SMTP_FROM_EMAIL", self.smtp_user)
            self.smtp_from_name = os.getenv("SMTP_FROM_NAME", "Visa Community Platform")
            
            if not self.smtp_user or not self.smtp_password:
                logger.warning("⚠️ SMTP credentials not configured - falling back to mock mode")
                self.mode = "mock"
        
        logger.info(f"📧 Email service initialized in '{self.mode}' mode")
    
    def send_verification_code(self, email: str, code: str, display_name: str) -> bool:
        """
        Send verification code to user email
        
        Args:
            email: Recipient email address
            code: Verification code (6 digits)
            display_name: User's display name
        
        Returns:
            bool: True if sent successfully
        """
        if self.mode == "mock":
            return self._send_mock(email, code, display_name)
        elif self.mode == "sendgrid":
            return self._send_sendgrid(email, code, display_name)
        elif self.mode == "aws_ses":
            return self._send_aws_ses(email, code, display_name)
        elif self.mode == "smtp":
            return self._send_smtp(email, code, display_name)
        else:
            logger.error(f"❌ Unknown email mode: {self.mode}")
            return False
    
    def _send_mock(self, email: str, code: str, display_name: str) -> bool:
        """Mock email sender - logs to console"""
        
        email_template = f"""
        ╔══════════════════════════════════════════════════════════════╗
        ║                📧 VERIFICATION CODE EMAIL                    ║
        ╚══════════════════════════════════════════════════════════════╝
        
        To: {email}
        Subject: Your Visa Community Platform Verification Code
        
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        Hi {display_name},
        
        Welcome to the Visa Community Platform!
        
        Your verification code is:
        
                            {code}
        
        This code will expire in 10 minutes.
        
        If you didn't request this code, please ignore this email.
        
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        Questions? Contact us at support@example.com
        
        © 2025 Visa Community Platform
        
        ╚══════════════════════════════════════════════════════════════╝
        """
        
        logger.info(email_template)
        logger.info(f"✅ Mock email sent to {email} with code: {code}")
        
        return True
    
    def _send_sendgrid(self, email: str, code: str, display_name: str) -> bool:
        """Send via SendGrid API"""
        try:
            # TODO: Implement SendGrid
            # from sendgrid import SendGridAPIClient
            # from sendgrid.helpers.mail import Mail
            
            logger.warning("⚠️ SendGrid not implemented yet - using mock mode")
            return self._send_mock(email, code, display_name)
        except Exception as e:
            logger.error(f"❌ SendGrid error: {e}")
            return False
    
    def _send_aws_ses(self, email: str, code: str, display_name: str) -> bool:
        """Send via AWS SES"""
        try:
            # TODO: Implement AWS SES
            # import boto3
            
            logger.warning("⚠️ AWS SES not implemented yet - using mock mode")
            return self._send_mock(email, code, display_name)
        except Exception as e:
            logger.error(f"❌ AWS SES error: {e}")
            return False
    
    def _send_smtp(self, email: str, code: str, display_name: str) -> bool:
        """Send via SMTP (Gmail, Outlook, etc.)"""
        try:
            # Log the code for debugging (DEV MODE)
            logger.info(f"📧 Sending verification code to {email}: {code}")
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Your Visa Community Platform Verification Code"
            msg["From"] = f"{self.smtp_from_name} <{self.smtp_from_email}>"
            msg["To"] = email
            
            # Email body (plain text)
            text_body = f"""
Hi {display_name},

Welcome to the Visa Community Platform!

Your verification code is: {code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

---
Questions? Contact us at support@example.com
© 2025 Visa Community Platform
            """
            
            # Email body (HTML)
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .code-box {{ background: white; border: 2px dashed #667eea; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; color: #667eea; margin: 20px 0; letter-spacing: 5px; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #999; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📧 Verification Code</h1>
                    </div>
                    <div class="content">
                        <p>Hi <strong>{display_name}</strong>,</p>
                        <p>Welcome to the Visa Community Platform!</p>
                        <p>Your verification code is:</p>
                        <div class="code-box">{code}</div>
                        <p>This code will expire in <strong>10 minutes</strong>.</p>
                        <p>If you didn't request this code, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>Questions? Contact us at support@example.com</p>
                        <p>© 2025 Visa Community Platform</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Attach both plain text and HTML versions
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            msg.attach(part1)
            msg.attach(part2)
            
            # Connect to SMTP server and send
            logger.info(f"📧 Connecting to {self.smtp_host}:{self.smtp_port}...")
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # Upgrade to secure connection
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email sent to {email} via SMTP")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ SMTP Authentication failed - check your email/password")
            logger.error("   For Gmail: Use an App Password, not your regular password")
            logger.error("   Generate at: https://myaccount.google.com/apppasswords")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending email: {e}")
            return False


# Global email service instance
# Mode is read from EMAIL_MODE environment variable (default: "mock")
email_service = EmailService(mode=os.getenv("EMAIL_MODE", "mock"))

