"""
User Authentication System with Email Verification
Implements secure login with unique verification codes
Powered by MongoDB for scalable user management
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import logging
from models.mongodb_auth import auth_db

logger = logging.getLogger(__name__)


class UserAuthDatabase:
    """MongoDB-based authentication database wrapper for backward compatibility"""
    
    def __init__(self):
        """Initialize authentication database (MongoDB)"""
        if not auth_db:
            logger.warning("⚠️  MongoDB auth database not available - authentication disabled")
            self.db = None
        else:
            self.db = auth_db
            logger.info("✅ User authentication database initialized (MongoDB)")
    
    def generate_verification_code(self, length: int = 6) -> str:
        """Generate a secure random verification code"""
        if not self.db: return ""
        return self.db.generate_verification_code(length)
    
    def generate_session_token(self) -> str:
        """Generate a secure session token"""
        if not self.db: return ""
        return self.db.generate_session_token()
    
    def create_or_get_user(self, email: str, display_name: str) -> Dict:
        """Create new user or get existing user by email"""
        if not self.db: return {}
        return self.db.create_or_get_user(email, display_name)
    
    def create_verification_code(self, user_id: str, expires_in_minutes: int = 10) -> str:
        """Create a new verification code for user"""
        if not self.db: return ""
        return self.db.create_verification_code(user_id, expires_in_minutes)
    
    def verify_code(self, email: str, code: str) -> Tuple[bool, Optional[Dict]]:
        """Verify the code and return user if valid"""
        if not self.db: return (False, None)
        return self.db.verify_code(email, code)
    
    def create_session(self, user_id: str, expires_in_days: int = 30) -> str:
        """Create a new session for user"""
        if not self.db: return ""
        return self.db.create_session(user_id, expires_in_days)
    
    def get_user_by_session(self, session_token: str) -> Optional[Dict]:
        """Get user by session token"""
        if not self.db: return None
        return self.db.get_user_by_session(session_token)
    
    def invalidate_session(self, session_token: str):
        """Invalidate a session (logout)"""
        if not self.db: return
        self.db.invalidate_session(session_token)
    
    def cleanup_expired_codes(self):
        """Delete expired verification codes (maintenance)"""
        if not self.db: return
        self.db.cleanup_expired_codes()
    
    def get_user_stats(self) -> Dict:
        """Get user statistics"""
        if not self.db: return {}
        return self.db.get_user_stats()
    
    def update_user_profile(self, user_id: str, display_name: str) -> Optional[Dict]:
        """Update user profile (display name)"""
        if not self.db: return None
        return self.db.update_user_profile(user_id, display_name)
    
    def is_user_banned(self, user_email: str) -> bool:
        """Check if user is currently banned"""
        if not self.db: return False
        return self.db.is_user_banned(user_email)


# Global auth database instance
auth_db_instance = UserAuthDatabase()

