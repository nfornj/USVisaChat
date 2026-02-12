"""
Email Service for sending verification codes
Supports: Mock (console), SMTP (Gmail/others), SendGrid, AWS SES
"""

import logging
import smtplib
import os
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# Import Google OAuth libraries only if available
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import pickle
    GMAIL_OAUTH_AVAILABLE = True
except ImportError:
    GMAIL_OAUTH_AVAILABLE = False

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending verification codes"""
    
    def __init__(self, mode: str = "mock"):
        """
        Initialize email service
        
        Args:
            mode: "mock" (console), "sendgrid", "aws_ses", "smtp", "gmail_oauth"
        """
        self.mode = mode
        self.gmail_service = None
        
        # Gmail OAuth configuration
        if mode == "gmail_oauth":
            if not GMAIL_OAUTH_AVAILABLE:
                logger.warning("⚠️  Gmail OAuth libraries not installed - falling back to mock mode")
                self.mode = "mock"
            else:
                self.gmail_from_email = os.getenv("GMAIL_FROM_EMAIL", "noreply@usvisachat.fly.dev")
                self.gmail_from_name = os.getenv("GMAIL_FROM_NAME", "Visa Community Platform")
                try:
                    self._setup_gmail_oauth()
                except Exception as e:
                    logger.error(f"❌ Gmail OAuth setup failed: {e}")
                    logger.warning("⚠️  Falling back to mock mode")
                    self.mode = "mock"
        
        # SMTP configuration from environment variables
        elif mode == "smtp":
            self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
            self.smtp_user = os.getenv("SMTP_USER", "")
            self.smtp_password = os.getenv("SMTP_PASSWORD", "")
            self.smtp_from_email = os.getenv("SMTP_FROM_EMAIL", self.smtp_user)
            self.smtp_from_name = os.getenv("SMTP_FROM_NAME", "Visa Community Platform")
            
            if not self.smtp_user or not self.smtp_password:
                logger.warning("⚠️  SMTP credentials not configured - falling back to mock mode")
                self.mode = "mock"
        
        logger.info(f"📧 Email service initialized in '{self.mode}' mode")
    
    def _setup_gmail_oauth(self):
        """Setup Gmail API with OAuth credentials"""
        SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        creds = None
        
        # Check for stored credentials
        token_path = '/app/token.pickle'  # In production container
        if not os.path.exists(token_path):
            token_path = 'token.pickle'  # Local development
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Look for client secret file
                client_secret_path = '/app/client_secret.json'
                if not os.path.exists(client_secret_path):
                    client_secret_path = 'client_secret_1061991869101-gbktfleonqno7o8moercglgi26p4b78d.apps.googleusercontent.com.json'
                
                if os.path.exists(client_secret_path):
                    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    raise FileNotFoundError("Gmail OAuth client secret file not found")
            
            # Save credentials for next run
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.gmail_service = build('gmail', 'v1', credentials=creds)
        logger.info("✅ Gmail OAuth service initialized")
    
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
        elif self.mode == "gmail_oauth":
            return self._send_gmail_oauth(email, code, display_name)
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
    
    def _send_gmail_oauth(self, email: str, code: str, display_name: str) -> bool:
        """Send via Gmail API with OAuth"""
        try:
            # Create email content
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
                        <p>Questions? Contact us at support@usvisachat.fly.dev</p>
                        <p>© 2025 Visa Community Platform</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            message = MIMEMultipart('alternative')
            message['to'] = email
            message['from'] = f"{self.gmail_from_name} <{self.gmail_from_email}>"
            message['subject'] = "Your Visa Community Platform Verification Code"
            
            message.attach(MIMEText(html_body, 'html'))
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send via Gmail API
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"✅ Email sent to {email} via Gmail OAuth")
            return True
            
        except Exception as e:
            logger.error(f"❌ Gmail OAuth send error: {e}")
            return False
    
    def _send_smtp(self, email: str, code: str, display_name: str) -> bool:
        """Send via SMTP (Gmail, Outlook, etc.)"""
        try:
            logger.info(f"📧 [SMTP] Preparing to send verification code to {email}")
            logger.info(f"🔑 [SMTP] Verification code: {code}")
            
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
            logger.info(f"🔌 [SMTP] Connecting to {self.smtp_host}:{self.smtp_port}...")
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                logger.info(f"🔐 [SMTP] Upgrading to TLS...")
                server.starttls()  # Upgrade to secure connection
                
                logger.info(f"🔑 [SMTP] Authenticating as {self.smtp_user}...")
                server.login(self.smtp_user, self.smtp_password)
                logger.info(f"✅ [SMTP] Authentication successful")
                
                logger.info(f"📨 [SMTP] Sending message...")
                server.send_message(msg)
                logger.info(f"✅ [SMTP] Message sent successfully")
            
            logger.info(f"✅✅✅ Email successfully delivered to {email} via SMTP")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌❌❌ [SMTP] Authentication FAILED for {self.smtp_user}")
            logger.error(f"❌ [SMTP] Error: {str(e)}")
            logger.error("❌ [SMTP] For Gmail: Use an App Password, not your regular password")
            logger.error("❌ [SMTP] Generate at: https://myaccount.google.com/apppasswords")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌❌❌ [SMTP] Send FAILED: {str(e)}")
            logger.error(f"❌ [SMTP] Recipient: {email}")
            return False
        except Exception as e:
            logger.error(f"❌❌❌ [SMTP] Unexpected error: {str(e)}")
            logger.error(f"❌ [SMTP] Recipient: {email}")
            import traceback
            logger.error(f"❌ [SMTP] Traceback: {traceback.format_exc()}")
            return False


# Global email service instance
# Auto-detect mode based on environment:
# - Production (ENVIRONMENT=production): Use gmail_oauth
# - Development (default): Use mock (logs to console)
def _get_email_mode():
    """Determine email mode based on environment"""
    # Allow explicit override via EMAIL_MODE
    explicit_mode = os.getenv("EMAIL_MODE")
    if explicit_mode:
        return explicit_mode
    
    # Auto-detect: production uses gmail_oauth, dev uses mock
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "production":
        return "gmail_oauth"
    else:
        return "mock"

email_service = EmailService(mode=_get_email_mode())

