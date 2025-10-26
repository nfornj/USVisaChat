"""
API Routes
Modular route handlers for the Visa platform
"""

from .auth import router as auth_router
from .chat import router as chat_router
from .search import router as search_router
from .news import router as news_router
from .test import router as test_router

__all__ = ['auth_router', 'chat_router', 'search_router', 'news_router', 'test_router']
