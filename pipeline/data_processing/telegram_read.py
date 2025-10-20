"""
Telegram Configuration and Utilities
Handles Telegram API configuration and session management
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """Load Telegram configuration from environment variables."""
    config = {
        "api_id": os.getenv("TELEGRAM_API_ID"),
        "api_hash": os.getenv("TELEGRAM_API_HASH"),
        "phone_or_token": os.getenv("TELEGRAM_PHONE_OR_BOT_TOKEN"),
        "twofa_password": os.getenv("TELEGRAM_2FA_PASSWORD"),
        "session_name": os.getenv("TELEGRAM_SESSION_NAME", "visa_telegram")
    }
    
    # Validate required fields
    required_fields = ["api_id", "api_hash", "phone_or_token"]
    missing_fields = [field for field in required_fields if not config[field]]
    
    if missing_fields:
        raise ValueError(f"Missing required Telegram configuration: {missing_fields}")
    
    logger.info("✅ Telegram configuration loaded successfully")
    return config

def is_bot_token(phone_or_token: str) -> bool:
    """Check if the provided string is a bot token."""
    # Bot tokens typically start with a number followed by a colon
    return ":" in phone_or_token and phone_or_token.split(":")[0].isdigit()

def ensure_session_path(session_name: str) -> str:
    """Ensure session directory exists and return session path."""
    session_dir = Path(".session")
    session_dir.mkdir(exist_ok=True)
    
    session_path = session_dir / session_name
    logger.info(f"📁 Session path: {session_path}")
    
    return str(session_path)

def validate_telegram_config() -> bool:
    """Validate that all required Telegram configuration is present."""
    try:
        config = load_config()
        return True
    except ValueError as e:
        logger.error(f"❌ Telegram configuration invalid: {e}")
        return False

def get_telegram_credentials() -> Dict[str, str]:
    """Get Telegram credentials for testing."""
    config = load_config()
    return {
        "api_id": config["api_id"],
        "api_hash": config["api_hash"],
        "phone_or_token": config["phone_or_token"],
        "is_bot": is_bot_token(config["phone_or_token"])
    }
