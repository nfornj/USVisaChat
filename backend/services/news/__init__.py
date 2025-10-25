"""
News Service Module
Provides news fetching from multiple sources (RSS, Google News) instead of Perplexity API
"""

from .news_service import NewsService
from .news_utils import (
    generate_comprehensive_ai_summary,
    generate_short_title,
    get_fallback_image,
    get_google_search_image,
    compress_image
)

__all__ = [
    'NewsService',
    'generate_comprehensive_ai_summary',
    'generate_short_title',
    'get_fallback_image',
    'get_google_search_image',
    'compress_image'
]
