"""
News Routes
Handles H1B/immigration news fetching, caching, and serving
Uses Perplexity SDK for news search
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException

from api.schemas import SearchRequest
from services.news import NewsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-news", tags=["news"])

# Global news service instance
news_service = None


def init_news_service():
    """Initialize news service"""
    global news_service
    news_service = NewsService()
    logger.info("✅ News service initialized")


@router.post("")
async def get_ai_news(request: SearchRequest):
    """
    AI News endpoint that returns cached H1B news or fetches fresh data if cache is empty
    """
    global news_service
    
    if not news_service:
        init_news_service()
    
    try:
        # Try to get cached articles first
        cached = news_service.get_cached_articles(limit=request.limit or 10)
        cache_status = news_service.get_cache_status()
        
        # Check if we have articles and they're fresh (< 24 hours old)
        if cached["has_articles"] and cache_status["cache_age_hours"] < 24:
            logger.info(f"✅ Returning {cached['total']} cached articles (age: {cache_status['cache_age_hours']:.1f}h)")
            return {
                **cached,
                "query": f"{request.query} H1B visa news latest updates 2024"
            }
        
        # If cache is empty or older than 24 hours, refresh in background
        if not cached["has_articles"]:
            logger.info("🔄 No cached articles found, fetching fresh data...")
        else:
            logger.info(f"⏰ Cache is {cache_status['cache_age_hours']:.1f}h old (>24h), refreshing...")
        
        refresh_result = news_service.refresh_cache(force=True)
        
        if refresh_result["success"]:
            cached = news_service.get_cached_articles(limit=request.limit or 10)
            return {
                **cached,
                "query": f"{request.query} H1B visa news latest updates 2024",
                "source": "fresh_fetch"
            }
        else:
            # Return mock data as fallback
            logger.warning("No cache and fetch failed, returning mock data")
            
            from services.news import get_fallback_image, generate_comprehensive_ai_summary
            from datetime import timedelta
            
            mock_articles = [
                {
                    "id": f"article-{i}",
                    "title": f"H1B Visa Processing Updates: New Guidelines for 2024 #{i+1}",
                    "summary": "Latest developments in H1B visa processing and policy changes affecting international workers in the tech industry.",
                    "content": "Recent updates to H1B visa processing have introduced new guidelines that affect thousands of international workers. The changes focus on streamlining the application process while maintaining security standards.",
                    "url": f"https://example.com/h1b-news/{i+1}",
                    "publishedAt": (datetime.now() - timedelta(hours=i*3)).isoformat(),
                    "source": f"Immigration News {i+1}",
                    "imageUrl": get_fallback_image(f"H1B Visa Processing Updates {i+1}", i),
                    "aiSummary": generate_comprehensive_ai_summary(
                        f"H1B Visa Processing Updates #{i+1}",
                        "Recent updates to H1B visa processing have introduced new guidelines that affect thousands of international workers."
                    ),
                    "tags": ["H1B", "Visa", "Immigration", "Work Visa", "Tech Industry"]
                }
                for i in range(min(request.limit or 8, 10))
            ]
            
            return {
                "articles": mock_articles,
                "total": len(mock_articles),
                "query": f"{request.query} H1B visa news latest updates 2024",
                "timestamp": datetime.now().isoformat(),
                "source": "mock_data",
                "note": "Using mock data - Perplexity API unavailable"
            }
        
    except Exception as e:
        logger.error(f"❌ AI News error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch AI news: {str(e)}")


@router.get("/status")
async def get_news_cache_status():
    """Get the current status of the news cache"""
    global news_service
    
    if not news_service:
        init_news_service()
    
    try:
        status = news_service.get_cache_status()
        return {"cache_status": status}
    except Exception as e:
        logger.error(f"❌ Cache status error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache status: {str(e)}")


@router.post("/refresh")
async def refresh_news_cache():
    """Manually trigger a news cache refresh"""
    global news_service
    
    if not news_service:
        init_news_service()
    
    try:
        result = news_service.refresh_cache(force=True)
        
        if result["success"]:
            return result
        else:
            return {
                **result,
                "message": result.get("message", "Failed to refresh cache")
            }
        
    except Exception as e:
        logger.error(f"❌ Manual refresh error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh news: {str(e)}")
