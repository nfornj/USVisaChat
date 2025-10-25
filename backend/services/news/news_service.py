"""
News Service using Perplexity Python SDK
Fetches H1B and immigration news using the official perplexityai library
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from perplexity import Perplexity

from .news_utils import (
    generate_comprehensive_ai_summary,
    generate_short_title,
    get_fallback_image
)

logger = logging.getLogger(__name__)


class NewsService:
    """
    News service using Perplexity Search API via official Python SDK
    """
    
    # Cache settings
    CACHE_EXPIRY_HOURS = 24
    MAX_CACHED_ARTICLES = 10
    MIN_FETCH_INTERVAL_HOURS = 24
    
    def __init__(self):
        """Initialize Perplexity client with API key from environment"""
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.client = None
        
        if self.api_key:
            try:
                self.client = Perplexity(api_key=self.api_key)
                logger.info("✅ Perplexity client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Perplexity client: {e}")
                self.client = None
        else:
            logger.warning("⚠️  PERPLEXITY_API_KEY not found in environment")
        
        # Cache structure
        self.cache = {
            "articles": [],
            "last_updated": None,
            "last_api_fetch": None,
            "is_fetching": False
        }
    
    def fetch_news(self, query: Optional[str] = None, max_results: int = 15) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch H1B news from Perplexity Search API using official SDK
        
        Args:
            query: Custom search query (default: comprehensive H1B/immigration query)
            max_results: Maximum number of results to fetch (default: 15)
        
        Returns:
            List of search results or None if fetch failed
        """
        try:
            # Check rate limiting
            if self.cache["last_api_fetch"]:
                hours_since_fetch = (datetime.now() - self.cache["last_api_fetch"]).total_seconds() / 3600
                if hours_since_fetch < self.MIN_FETCH_INTERVAL_HOURS:
                    logger.info(f"⏳ Perplexity API called {hours_since_fetch:.1f}h ago. Skipping (minimum {self.MIN_FETCH_INTERVAL_HOURS}h interval)")
                    return None
            
            if not self.client:
                logger.warning("Perplexity client not initialized")
                return None
            
            # Default comprehensive H1B/immigration query
            if not query:
                query = (
                    "H1B visa breaking news updates green card processing EB-2 EB-3 "
                    "priority dates PERM labor certification I-140 I-485 processing times "
                    "USCIS policy changes premium processing delays RFE responses visa bulletin "
                    "employment-based immigration OPT STEM extension cap gap H-4 EAD work authorization"
                )
            
            logger.info(f"🔍 Fetching H1B news from Perplexity using SDK (query: {len(query)} chars)...")
            
            # Use official SDK with search domains filter
            search = self.client.search.create(
                query=query,
                max_results=max_results,
                max_tokens_per_page=2048,
                search_domain_filter=[
                    "immihelp.com",
                    "redbus2us.com",
                    "newsweek.com",
                    "uscis.gov",
                    "cnn.com",
                    "bbc.com"
                ]
            )
            
            # Track successful API call
            self.cache["last_api_fetch"] = datetime.now()
            
            # Extract results from SDK response
            results = []
            if hasattr(search, 'results') and search.results:
                for result in search.results:
                    results.append({
                        'title': result.title if hasattr(result, 'title') else 'Untitled',
                        'content': result.content if hasattr(result, 'content') else result.snippet if hasattr(result, 'snippet') else '',
                        'url': result.url if hasattr(result, 'url') else '#',
                        'published_date': result.published_date if hasattr(result, 'published_date') else datetime.now().isoformat(),
                        'site': result.site if hasattr(result, 'site') else 'Immigration News'
                    })
            
            logger.info(f"✅ Successfully fetched {len(results)} news articles from Perplexity SDK")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching news from Perplexity SDK: {e}")
            return None
    
    def process_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process Perplexity search results into article format with AI enhancements
        
        Args:
            results: Raw search results from Perplexity
        
        Returns:
            Processed articles with AI summaries, images, and metadata
        """
        if not results:
            return []
        
        articles = []
        for i, result in enumerate(results[:12]):  # Limit to 12 articles
            try:
                original_title = result.get('title', f'H1B Visa News Update #{i+1}')
                content = result.get('content', result.get('snippet', ''))
                url = result.get('url', f'https://example.com/h1b-news/{i+1}')
                published_at = result.get('published_date', datetime.now().isoformat())
                source = result.get('site', 'Immigration News')
                
                # Generate SHORT title using Groq
                short_title = generate_short_title(original_title, content)
                
                # Generate AI summary
                ai_summary = generate_comprehensive_ai_summary(original_title, content)
                
                # Generate image topic for better images
                image_topic = f"{original_title} immigration visa"
                
                article = {
                    "id": f"article-{i}",
                    "title": short_title,
                    "summary": content[:300] + "..." if len(content) > 300 else content,
                    "content": content,
                    "url": url,
                    "publishedAt": published_at,
                    "source": source,
                    "imageUrl": get_fallback_image(image_topic, i),
                    "aiSummary": ai_summary,
                    "tags": ["H1B", "Visa", "Immigration", "Work Visa", "Tech Industry"]
                }
                articles.append(article)
                
            except Exception as e:
                logger.error(f"Error processing article {i}: {e}")
                continue
        
        return articles
    
    def merge_articles_intelligently(
        self, 
        new_articles: List[Dict[str, Any]], 
        existing_articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge new articles with existing cache intelligently
        - Keep latest articles first
        - Remove duplicates based on URL
        - Maintain MAX_CACHED_ARTICLES limit
        """
        if not new_articles:
            return existing_articles[:self.MAX_CACHED_ARTICLES]
        
        # Create set of existing URLs for duplicate detection
        existing_urls = {article.get('url', '') for article in existing_articles}
        
        # Filter out duplicates from new articles
        unique_new_articles = [
            article for article in new_articles 
            if article.get('url', '') not in existing_urls
        ]
        
        # Combine existing and new articles
        all_articles = unique_new_articles + existing_articles
        
        # Sort by published date (newest first)
        all_articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
        
        # Keep only most recent articles
        return all_articles[:self.MAX_CACHED_ARTICLES]
    
    def get_cached_articles(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get cached articles with metadata
        
        Args:
            limit: Maximum number of articles to return
        
        Returns:
            Dictionary with articles and cache metadata
        """
        cache_age_hours = 0
        if self.cache["last_updated"]:
            cache_age_hours = round(
                (datetime.now() - self.cache["last_updated"]).total_seconds() / 3600, 
                1
            )
        
        return {
            "articles": self.cache["articles"][:limit],
            "total": len(self.cache["articles"][:limit]),
            "timestamp": self.cache["last_updated"].isoformat() if self.cache["last_updated"] else datetime.now().isoformat(),
            "source": "cache",
            "cache_age_hours": cache_age_hours,
            "has_articles": len(self.cache["articles"]) > 0
        }
    
    def is_cache_expired(self) -> bool:
        """Check if cache is expired"""
        if not self.cache["last_updated"]:
            return True
        
        cache_age_hours = (datetime.now() - self.cache["last_updated"]).total_seconds() / 3600
        return cache_age_hours > self.CACHE_EXPIRY_HOURS
    
    def refresh_cache(self, force: bool = False) -> Dict[str, Any]:
        """
        Refresh news cache from Perplexity
        
        Args:
            force: Force refresh even if cache is not expired
        
        Returns:
            Result dictionary with status and message
        """
        if self.cache["is_fetching"]:
            return {"success": False, "message": "News fetch already in progress", "status": "fetching"}
        
        if not force and not self.is_cache_expired():
            return {"success": False, "message": "Cache is still fresh", "status": "cached"}
        
        self.cache["is_fetching"] = True
        logger.info("🔄 Refreshing news cache...")
        
        try:
            # Fetch from Perplexity using SDK
            results = self.fetch_news()
            
            if results:
                new_articles = self.process_results(results)
                if new_articles:
                    # Merge with existing cache
                    merged_articles = self.merge_articles_intelligently(
                        new_articles,
                        self.cache["articles"]
                    )
                    self.cache["articles"] = merged_articles
                    self.cache["last_updated"] = datetime.now()
                    
                    new_count = len([
                        a for a in new_articles 
                        if a.get('url', '') not in {e.get('url', '') for e in self.cache["articles"]}
                    ])
                    
                    logger.info(f"✅ Updated cache with {len(merged_articles)} total articles ({new_count} new)")
                    
                    return {
                        "success": True,
                        "message": f"Successfully refreshed cache with {len(merged_articles)} total articles ({new_count} new)",
                        "status": "success",
                        "article_count": len(merged_articles)
                    }
                else:
                    logger.warning("No articles processed from Perplexity data")
                    return {"success": False, "message": "No articles processed", "status": "failed"}
            else:
                logger.warning("Failed to fetch from Perplexity")
                return {"success": False, "message": "Failed to fetch from Perplexity", "status": "failed"}
                
        except Exception as e:
            logger.error(f"Error refreshing cache: {e}")
            return {"success": False, "message": f"Error: {str(e)}", "status": "error"}
        finally:
            self.cache["is_fetching"] = False
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get current cache status"""
        cache_age_hours = 0
        if self.cache["last_updated"]:
            cache_age_hours = round(
                (datetime.now() - self.cache["last_updated"]).total_seconds() / 3600,
                1
            )
        
        return {
            "has_articles": len(self.cache["articles"]) > 0,
            "article_count": len(self.cache["articles"]),
            "last_updated": self.cache["last_updated"].isoformat() if self.cache["last_updated"] else None,
            "cache_age_hours": cache_age_hours,
            "is_fetching": self.cache["is_fetching"],
            "is_expired": cache_age_hours > self.CACHE_EXPIRY_HOURS if self.cache["last_updated"] else True,
            "perplexity_available": self.client is not None
        }
