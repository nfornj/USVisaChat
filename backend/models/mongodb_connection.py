"""
MongoDB Connection Manager
Supports certificate-based authentication for MongoDB Atlas with validation
"""

import os
import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
from urllib.parse import quote_plus
from pathlib import Path

logger = logging.getLogger(__name__)


class MongoDBConnection:
    """MongoDB connection manager with certificate authentication support"""
    
    def __init__(self):
        """Initialize MongoDB connection from environment variables"""
        self.client: Optional[MongoClient] = None
        self.db = None
        self.database_name = os.getenv("MONGODB_DATABASE", "visa_community")
        
        # Connection configuration
        self.connection_string = os.getenv("MONGODB_URI", "")
        self.auth_mechanism = os.getenv("MONGODB_AUTH_MECHANISM", "SCRAM-SHA-256")
        
        # Certificate-based authentication
        self.tls_enabled = os.getenv("MONGODB_TLS_ENABLED", "true").lower() == "true"
        self.tls_cert_file = os.getenv("MONGODB_TLS_CERT_FILE", "")  # Path to client certificate
        self.tls_ca_file = os.getenv("MONGODB_TLS_CA_FILE", "")      # Path to CA certificate
        
        # Username/password authentication (alternative)
        self.username = os.getenv("MONGODB_USERNAME", "")
        self.password = os.getenv("MONGODB_PASSWORD", "")
        self.host = os.getenv("MONGODB_HOST", "localhost")
        self.port = int(os.getenv("MONGODB_PORT", "27017"))
        
        self._connect()
    
    def _build_connection_string(self) -> str:
        """Build MongoDB connection string based on configuration"""
        
        # If connection string is provided, use it directly
        if self.connection_string:
            logger.info("Using provided MongoDB connection string")
            return self.connection_string
        
        # Build connection string from components
        if self.username and self.password:
            # Username/password authentication
            auth_part = f"{quote_plus(self.username)}:{quote_plus(self.password)}@"
            logger.info(f"Using username/password authentication for {self.username}")
        else:
            auth_part = ""
            logger.info("Using certificate-based or no authentication")
        
        # Check if it's an Atlas cluster (SRV format)
        if ".mongodb.net" in self.host:
            connection_string = f"mongodb+srv://{auth_part}{self.host}/{self.database_name}"
        else:
            connection_string = f"mongodb://{auth_part}{self.host}:{self.port}/{self.database_name}"
        
        return connection_string
    
    def _validate_certificate_files(self) -> bool:
        """Validate certificate files before connection"""
        if not self.tls_enabled:
            return True
        
        all_valid = True
        
        # Validate client certificate if provided
        if self.tls_cert_file:
            if not Path(self.tls_cert_file).exists():
                logger.error(f"❌ Client certificate not found: {self.tls_cert_file}")
                all_valid = False
            else:
                logger.info(f"✅ Client certificate found: {self.tls_cert_file}")
                
                # Check file permissions
                try:
                    file_stat = os.stat(self.tls_cert_file)
                    if file_stat.st_mode & 0o004:  # World-readable
                        logger.warning(
                            f"⚠️  Client certificate is world-readable. "
                            f"Consider: chmod 600 {self.tls_cert_file}"
                        )
                except Exception as e:
                    logger.warning(f"⚠️  Could not check certificate permissions: {e}")
        
        # Validate CA certificate if provided
        if self.tls_ca_file:
            if not Path(self.tls_ca_file).exists():
                logger.error(f"❌ CA certificate not found: {self.tls_ca_file}")
                all_valid = False
            else:
                logger.info(f"✅ CA certificate found: {self.tls_ca_file}")
        
        # For X.509 auth, client certificate is required
        if self.auth_mechanism == "MONGODB-X509" and not self.tls_cert_file:
            logger.error("❌ MONGODB-X509 authentication requires a client certificate")
            all_valid = False
        
        return all_valid
    
    def _get_connection_options(self) -> dict:
        """Get connection options including TLS/certificate settings and connection pooling"""
        options = {
            # Connection timeouts
            "serverSelectionTimeoutMS": 5000,  # 5 second timeout
            "connectTimeoutMS": 10000,          # 10 second connection timeout
            "socketTimeoutMS": 45000,           # 45 second socket timeout
            
            # Connection pooling (optimized for 1000+ concurrent users)
            "maxPoolSize": 100,                 # Max 100 connections in pool
            "minPoolSize": 10,                  # Keep 10 connections warm
            "maxIdleTimeMS": 30000,             # Idle connections closed after 30s
            "waitQueueTimeoutMS": 5000,         # Wait max 5s for connection from pool
            
            # Write settings
            "retryWrites": True,
            "w": "majority"                     # Write concern
        }
        
        # If using full connection URI (with credentials embedded), don't add auth options
        if self.connection_string and '@' in self.connection_string:
            logger.info("🔗 Using full connection URI with embedded credentials")
            # Just enable TLS if configured
            if self.tls_enabled:
                options["tls"] = True
            return options
        
        # Add TLS/Certificate options (only for certificate-based auth)
        if self.tls_enabled:
            options["tls"] = True
            
            # Only add certificate if file exists and we're using X.509
            if self.auth_mechanism == "MONGODB-X509" and self.tls_cert_file:
                if Path(self.tls_cert_file).exists():
                    logger.info(f"📜 Using client certificate: {self.tls_cert_file}")
                    options["tlsCertificateKeyFile"] = self.tls_cert_file
                    options["tlsAllowInvalidCertificates"] = True
                    options["tlsAllowInvalidHostnames"] = True
                else:
                    logger.warning(f"⚠️  Certificate file not found, skipping X.509: {self.tls_cert_file}")
            
            if self.tls_ca_file and Path(self.tls_ca_file).exists():
                logger.info(f"📜 Using CA certificate: {self.tls_ca_file}")
                options["tlsCAFile"] = self.tls_ca_file
        
        # Add authentication mechanism (only if not using full URI)
        if self.auth_mechanism:
            if self.auth_mechanism == "MONGODB-X509" and self.tls_cert_file and Path(self.tls_cert_file).exists():
                # X.509 auth requires certificate
                options["authMechanism"] = "MONGODB-X509"
                logger.info("🔐 Using X.509 certificate authentication")
            elif self.auth_mechanism != "MONGODB-X509" and self.username:
                # Username/password authentication
                options["authMechanism"] = self.auth_mechanism
                logger.info(f"🔐 Using {self.auth_mechanism} authentication with username")
        
        return options
    
    def _connect(self):
        """Establish connection to MongoDB"""
        try:
            # Print to stdout (will always appear)
            print("="*60)
            print("🔌 MONGODB CONNECTION DEBUG")
            print("="*60)
            print(f"📋 Configuration:")
            print(f"   MONGODB_URI set: {bool(os.getenv('MONGODB_URI'))}")
            print(f"   MONGODB_DATABASE: {self.database_name}")
            print(f"   MONGODB_TLS_ENABLED: {self.tls_enabled}")
            print(f"   MONGODB_AUTH_MECHANISM: {self.auth_mechanism}")
            print(f"   MONGODB_USERNAME set: {bool(self.username)}")
            print(f"   MONGODB_PASSWORD set: {bool(self.password)}")
            print(f"   MONGODB_HOST: {self.host}")
            print(f"   TLS_CERT_FILE: {self.tls_cert_file}")
            print(f"   TLS_CA_FILE: {self.tls_ca_file}")
            
            logger.info("="*60)
            logger.info("🔌 MONGODB CONNECTION DEBUG")
            logger.info("="*60)
            
            # Log environment variables (sanitized)
            logger.info(f"📋 Configuration:")
            logger.info(f"   MONGODB_URI set: {bool(os.getenv('MONGODB_URI'))}")
            logger.info(f"   MONGODB_DATABASE: {self.database_name}")
            logger.info(f"   MONGODB_TLS_ENABLED: {self.tls_enabled}")
            logger.info(f"   MONGODB_AUTH_MECHANISM: {self.auth_mechanism}")
            logger.info(f"   MONGODB_USERNAME set: {bool(self.username)}")
            logger.info(f"   MONGODB_PASSWORD set: {bool(self.password)}")
            logger.info(f"   MONGODB_HOST: {self.host}")
            logger.info(f"   TLS_CERT_FILE: {self.tls_cert_file}")
            logger.info(f"   TLS_CA_FILE: {self.tls_ca_file}")
            
            # Validate certificates first
            if not self._validate_certificate_files():
                logger.warning("⚠️  Certificate validation failed, continuing with username/password")
            
            connection_string = self._build_connection_string()
            connection_options = self._get_connection_options()
            
            # Log connection string (sanitized)
            sanitized_uri = connection_string
            if '@' in sanitized_uri:
                parts = sanitized_uri.split('@')
                if '://' in parts[0]:
                    protocol = parts[0].split('://')[0]
                    sanitized_uri = f"{protocol}://***:***@{parts[1]}"
            logger.info(f"📡 Connection URI: {sanitized_uri}")
            
            logger.info("🔌 Connecting to MongoDB...")
            logger.info(f"   Database: {self.database_name}")
            logger.info(f"   TLS Enabled: {self.tls_enabled}")
            logger.info(f"   Auth Mechanism: {self.auth_mechanism}")
            logger.info(f"   Connection Options: {list(connection_options.keys())}")
            
            # Create MongoDB client
            logger.info("🛠️  Creating MongoDB client...")
            self.client = MongoClient(connection_string, **connection_options)
            
            # Test connection
            logger.info("🏓 Testing connection with ping command...")
            ping_result = self.client.admin.command('ping')
            logger.info(f"✅ Ping successful: {ping_result}")
            
            # Get database
            self.db = self.client[self.database_name]
            
            # Get server info
            server_info = self.client.server_info()
            logger.info("="*60)
            logger.info(f"✅ Connected to MongoDB successfully!")
            logger.info(f"   Server Version: {server_info['version']}")
            logger.info(f"   Database: {self.database_name}")
            logger.info(f"   Connection: Active")
            logger.info("="*60)
            
        except ConnectionFailure as e:
            logger.error("="*60)
            logger.error(f"❌ MongoDB ConnectionFailure: {type(e).__name__}")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Connection String (sanitized): {sanitized_uri}")
            logger.error(f"   TLS Enabled: {self.tls_enabled}")
            logger.error(f"   Auth Mechanism: {self.auth_mechanism}")
            
            # Check specific error types
            error_str = str(e).lower()
            if 'timeout' in error_str:
                logger.error("🕒 Issue: Connection timeout - check network/firewall")
            if 'authentication' in error_str or 'auth' in error_str:
                logger.error("🔐 Issue: Authentication failed - check username/password")
            if 'ssl' in error_str or 'tls' in error_str:
                logger.error("🔒 Issue: SSL/TLS error - check certificates and TLS settings")
            if 'dns' in error_str or 'hostname' in error_str:
                logger.error("🌐 Issue: DNS/hostname resolution failed")
            
            logger.error("="*60)
            logger.warning("⚠️  Continuing without MongoDB (some features may be limited)")
            self.client = None
            self.db = None
        except ConfigurationError as e:
            logger.error("="*60)
            logger.error(f"❌ MongoDB ConfigurationError: {type(e).__name__}")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Check environment variables and options")
            logger.error("="*60)
            logger.warning("⚠️  Continuing without MongoDB (some features may be limited)")
            self.client = None
            self.db = None
        except Exception as e:
            logger.error("="*60)
            logger.error(f"❌ Unexpected MongoDB error: {type(e).__name__}")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Error type: {type(e).__module__}.{type(e).__name__}")
            import traceback
            logger.error(f"   Traceback:\n{traceback.format_exc()}")
            logger.error("="*60)
            logger.warning("⚠️  Continuing without MongoDB (some features may be limited)")
            self.client = None
            self.db = None
    
    def get_collection(self, collection_name: str):
        """Get a MongoDB collection"""
        if self.db is None:
            raise Exception("MongoDB not connected")
        return self.db[collection_name]
    
    def create_indexes(self):
        """Create all necessary indexes for optimal performance"""
        if self.db is None:
            logger.error("Cannot create indexes - not connected to MongoDB")
            return
        
        logger.info("📊 Creating MongoDB indexes...")
        
        try:
            # Users collection indexes (with new fields)
            users = self.db.users
            users.create_index("email", unique=True, name="idx_users_email")
            users.create_index("is_verified", name="idx_users_verified")
            users.create_index("last_login_at", name="idx_users_last_login")
            
            # New indexes for moderation and stats
            users.create_index("role", name="idx_users_role")
            users.create_index("banned", name="idx_users_banned")
            users.create_index(
                [("banned", 1), ("ban_expires_at", 1)],
                name="idx_users_banned_expires"
            )
            users.create_index("stats.message_count", name="idx_users_message_count")
            users.create_index("stats.last_active", name="idx_users_last_active")
            
            logger.info("   ✅ Users indexes created (with moderation & stats)")
            
            # Messages collection indexes (optimized for 1000+ users)
            messages = self.db.messages
            
            # Primary query indexes
            messages.create_index([("created_at", -1)], name="idx_messages_created_desc")
            messages.create_index([("user_email", 1), ("created_at", -1)], name="idx_messages_user_created")
            messages.create_index([("room_id", 1), ("created_at", -1)], name="idx_messages_room_created")
            
            # Compound index for room + deleted filter (most common query)
            messages.create_index(
                [("room_id", 1), ("deleted", 1), ("created_at", -1)],
                name="idx_messages_room_deleted_created"
            )
            
            # Topic/thread index for conversation threading
            messages.create_index(
                [("topic_id", 1), ("created_at", 1)],
                name="idx_messages_topic_created"
            )
            
            # Text search index (for message search feature)
            try:
                messages.create_index(
                    [("message", "text")],
                    name="idx_messages_text_search"
                )
                logger.info("   ✅ Messages text search index created")
            except Exception as e:
                logger.warning(f"   ⚠️  Text index already exists or error: {e}")
            
            # Indexes for new rich content fields
            messages.create_index("mentioned_users", name="idx_messages_mentions")
            messages.create_index("reply_count", name="idx_messages_reply_count")
            
            logger.info("   ✅ Messages indexes created (with rich content)")
            
            # Sessions collection indexes with TTL
            sessions = self.db.sessions
            sessions.create_index("session_token", unique=True, name="idx_sessions_token")
            sessions.create_index([("user_id", 1), ("is_active", 1)], name="idx_sessions_user_active")
            sessions.create_index("expires_at", expireAfterSeconds=0, name="idx_sessions_ttl")  # TTL index
            logger.info("   ✅ Sessions indexes created (with TTL)")
            
            # Verification codes collection indexes with TTL
            codes = self.db.verification_codes
            codes.create_index([("code", 1), ("user_id", 1)], name="idx_codes_code_user")
            codes.create_index("expires_at", expireAfterSeconds=0, name="idx_codes_ttl")  # TTL index
            codes.create_index([("user_id", 1), ("created_at", -1)], name="idx_codes_user_created")
            logger.info("   ✅ Verification codes indexes created (with TTL)")
            
            logger.info("✅ All indexes created successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error creating indexes: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test if MongoDB connection is alive"""
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Get database statistics"""
        if self.db is None:
            return {}
        
        try:
            stats = {
                'database': self.database_name,
                'collections': {},
                'total_documents': 0
            }
            
            for collection_name in ['users', 'messages', 'sessions', 'verification_codes']:
                count = self.db[collection_name].count_documents({})
                stats['collections'][collection_name] = count
                stats['total_documents'] += count
            
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


# Global MongoDB connection instance
# Initialize on first import
try:
    mongodb_client = MongoDBConnection()
except Exception as e:
    logger.error(f"Failed to initialize MongoDB connection: {e}")
    logger.error("Application will not function properly without MongoDB")
    mongodb_client = None
