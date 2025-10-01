"""
MongoDB Authentication Database
Handles user authentication, verification codes, and sessions
"""

import logging
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from bson import ObjectId
from mongodb_connection import mongodb_client

logger = logging.getLogger(__name__)


class MongoDBAuthDatabase:
    """MongoDB-based authentication database"""
    
    def __init__(self):
        """Initialize MongoDB auth database"""
        if mongodb_client is None or mongodb_client.db is None:
            raise Exception("MongoDB connection not available")
        
        self.db = mongodb_client.db
        self.users = self.db.users
        self.verification_codes = self.db.verification_codes
        self.sessions = self.db.sessions
        
        logger.info("✅ MongoDB Auth Database initialized")
    
    def generate_verification_code(self, length: int = 6) -> str:
        """Generate a secure random verification code"""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    def generate_session_token(self) -> str:
        """Generate a secure session token"""
        return secrets.token_urlsafe(32)
    
    def create_or_get_user(self, email: str, display_name: str) -> Dict:
        """
        Create new user or get existing user by email
        
        Args:
            email: User's email address
            display_name: User's display name
        
        Returns:
            Dict: User document
        """
        try:
            # Normalize email
            email = email.lower().strip()
            display_name = display_name.strip()
            
            # Check if user exists
            user = self.users.find_one({'email': email})
            
            if user:
                # Update display name if changed
                if user.get('display_name') != display_name:
                    self.users.update_one(
                        {'_id': user['_id']},
                        {
                            '$set': {
                                'display_name': display_name,
                                'updated_at': datetime.now(timezone.utc)
                            }
                        }
                    )
                    user['display_name'] = display_name
                
                logger.info(f"✅ Existing user retrieved: {email}")
            else:
                # Create new user
                user_doc = {
                    'email': email,
                    'display_name': display_name,
                    'is_verified': False,
                    'profile': {
                        'avatar_url': None,
                        'bio': None,
                        'timezone': 'UTC'
                    },
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc),
                    'last_login_at': None
                }
                
                result = self.users.insert_one(user_doc)
                user = self.users.find_one({'_id': result.inserted_id})
                
                logger.info(f"✅ New user created: {email}")
            
            return self._format_user(user)
            
        except Exception as e:
            logger.error(f"❌ Error creating/getting user: {e}")
            raise
    
    def create_verification_code(
        self, 
        user_id: str, 
        expires_in_minutes: int = 10
    ) -> str:
        """
        Create a new verification code for user
        
        Args:
            user_id: User's ID (can be string or ObjectId)
            expires_in_minutes: Code expiration time in minutes
        
        Returns:
            str: Generated verification code
        """
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            # Invalidate any previous unused codes for this user
            # (MongoDB TTL will auto-delete expired ones)
            self.verification_codes.update_many(
                {
                    'user_id': user_id,
                    'used': False
                },
                {
                    '$set': {
                        'used': True,
                        'used_at': datetime.now(timezone.utc)
                    }
                }
            )
            
            # Generate new code
            code = self.generate_verification_code()
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
            
            # Store code
            code_doc = {
                'user_id': user_id,
                'code': code,
                'created_at': datetime.now(timezone.utc),
                'expires_at': expires_at,
                'used': False,
                'used_at': None
            }
            
            self.verification_codes.insert_one(code_doc)
            
            logger.info(f"✅ Verification code created for user_id={user_id}, expires in {expires_in_minutes}min")
            return code
            
        except Exception as e:
            logger.error(f"❌ Error creating verification code: {e}")
            raise
    
    def verify_code(self, email: str, code: str) -> Tuple[bool, Optional[Dict]]:
        """
        Verify the code and return user if valid
        
        Args:
            email: User's email
            code: Verification code to verify
        
        Returns:
            Tuple[bool, Optional[Dict]]: (success, user_data)
        """
        try:
            email = email.lower().strip()
            
            # Get user
            user = self.users.find_one({'email': email})
            
            if not user:
                logger.warning(f"❌ User not found: {email}")
                return False, None
            
            user_id = user['_id']
            
            # Find the most recent code for this user
            code_record = self.verification_codes.find_one(
                {
                    'user_id': user_id,
                    'code': code
                },
                sort=[('created_at', -1)]
            )
            
            if not code_record:
                logger.warning(f"❌ Invalid verification code for {email}")
                return False, None
            
            # Check if already used
            if code_record.get('used'):
                logger.warning(f"❌ Verification code already used for {email}")
                return False, None
            
            # Check if expired
            expires_at = code_record['expires_at']
            # Ensure timezone-aware comparison
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if datetime.now(timezone.utc) > expires_at:
                logger.warning(f"❌ Verification code expired for {email}")
                return False, None
            
            # Mark code as used
            self.verification_codes.update_one(
                {'_id': code_record['_id']},
                {
                    '$set': {
                        'used': True,
                        'used_at': datetime.now(timezone.utc)
                    }
                }
            )
            
            # Mark user as verified and update last login
            self.users.update_one(
                {'_id': user_id},
                {
                    '$set': {
                        'is_verified': True,
                        'last_login_at': datetime.now(timezone.utc)
                    }
                }
            )
            
            # Get updated user data
            user = self.users.find_one({'_id': user_id})
            
            logger.info(f"✅ Code verified successfully for {email}")
            return True, self._format_user(user)
            
        except Exception as e:
            logger.error(f"❌ Error verifying code: {e}")
            return False, None
    
    def create_session(
        self, 
        user_id: str, 
        expires_in_days: int = 30,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Create a new session for user
        
        Args:
            user_id: User's ID
            expires_in_days: Session expiration time in days
            metadata: Additional session metadata (user_agent, IP, etc.)
        
        Returns:
            str: Session token
        """
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            session_token = self.generate_session_token()
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            
            session_doc = {
                'user_id': user_id,
                'session_token': session_token,
                'created_at': datetime.now(timezone.utc),
                'expires_at': expires_at,
                'is_active': True,
                'last_activity': datetime.now(timezone.utc),
                'metadata': metadata or {}
            }
            
            self.sessions.insert_one(session_doc)
            
            logger.info(f"✅ Session created for user_id={user_id}")
            return session_token
            
        except Exception as e:
            logger.error(f"❌ Error creating session: {e}")
            raise
    
    def get_user_by_session(self, session_token: str) -> Optional[Dict]:
        """
        Get user by session token
        
        Args:
            session_token: Session token
        
        Returns:
            Optional[Dict]: User document if session is valid
        """
        try:
            # Find active, non-expired session
            session = self.sessions.find_one({
                'session_token': session_token,
                'is_active': True,
                'expires_at': {'$gt': datetime.now(timezone.utc)}
            })
            
            if not session:
                return None
            
            # Update last activity
            self.sessions.update_one(
                {'_id': session['_id']},
                {'$set': {'last_activity': datetime.now(timezone.utc)}}
            )
            
            # Get user
            user = self.users.find_one({'_id': session['user_id']})
            
            if user:
                return self._format_user(user)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user by session: {e}")
            return None
    
    def invalidate_session(self, session_token: str):
        """
        Invalidate a session (logout)
        
        Args:
            session_token: Session token to invalidate
        """
        try:
            result = self.sessions.update_one(
                {'session_token': session_token},
                {'$set': {'is_active': False}}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Session invalidated")
            
        except Exception as e:
            logger.error(f"❌ Error invalidating session: {e}")
    
    def cleanup_expired_codes(self):
        """
        Delete expired verification codes
        Note: With TTL index, MongoDB auto-deletes expired documents
        This is a manual cleanup for systems without TTL
        """
        try:
            result = self.verification_codes.delete_many({
                'expires_at': {'$lt': datetime.now(timezone.utc)}
            })
            
            if result.deleted_count > 0:
                logger.info(f"✅ Cleaned up {result.deleted_count} expired verification codes")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up codes: {e}")
    
    def get_user_stats(self) -> Dict:
        """Get user statistics"""
        try:
            total_users = self.users.count_documents({})
            verified_users = self.users.count_documents({'is_verified': True})
            active_sessions = self.sessions.count_documents({
                'is_active': True,
                'expires_at': {'$gt': datetime.now(timezone.utc)}
            })
            
            return {
                'total_users': total_users,
                'verified_users': verified_users,
                'active_sessions': active_sessions
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting user stats: {e}")
            return {}
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email address"""
        try:
            email = email.lower().strip()
            user = self.users.find_one({'email': email})
            
            if user:
                return self._format_user(user)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user by email: {e}")
            return None
    
    def update_user_profile(self, user_id: str, display_name: str) -> Optional[Dict]:
        """
        Update user profile (display name)
        
        Args:
            user_id: User's ID (string or ObjectId)
            display_name: New display name
        
        Returns:
            Optional[Dict]: Updated user document
        """
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            display_name = display_name.strip()
            
            # Update the user
            self.users.update_one(
                {'_id': user_id},
                {
                    '$set': {
                        'display_name': display_name,
                        'updated_at': datetime.now(timezone.utc)
                    }
                }
            )
            
            # Get and return updated user
            user = self.users.find_one({'_id': user_id})
            
            if user:
                logger.info(f"✅ Updated display name for user_id={user_id} to '{display_name}'")
                return self._format_user(user)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error updating user profile: {e}")
            return None
    
    def _format_user(self, user_doc: Dict) -> Dict:
        """Format user document for API response"""
        if not user_doc:
            return {}
        
        return {
            'id': str(user_doc['_id']),
            'email': user_doc['email'],
            'display_name': user_doc['display_name'],
            'is_verified': user_doc.get('is_verified', False),
            'created_at': user_doc.get('created_at'),
            'last_login_at': user_doc.get('last_login_at')
        }


# Global auth database instance
try:
    auth_db = MongoDBAuthDatabase()
except Exception as e:
    logger.error(f"Failed to initialize MongoDB auth database: {e}")
    auth_db = None
