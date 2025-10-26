"""
News Service using Perplexity Python SDK
Fetches H1B and immigration news using the official perplexityai library
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from perplexity import Perplexity
import concurrent.futures

from .news_utils import (
    generate_comprehensive_ai_summary,
    generate_short_title,
    get_fallback_image
)
from .article_scraper import scrape_with_fallback
from models.news import news_model

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
        self.news_model = news_model
        
        if self.api_key:
            try:
                self.client = Perplexity(api_key=self.api_key)
                logger.info("✅ Perplexity client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Perplexity client: {e}")
                self.client = None
        else:
            logger.warning("⚠️  PERPLEXITY_API_KEY not found in environment")
        
        # In-memory cache for last API fetch time only
        self.last_api_fetch = None
    
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
            if self.last_api_fetch:
                hours_since_fetch = (datetime.now() - self.last_api_fetch).total_seconds() / 3600
                if hours_since_fetch < self.MIN_FETCH_INTERVAL_HOURS:
                    logger.info(f"⏳ Perplexity API called {hours_since_fetch:.1f}h ago. Skipping (minimum {self.MIN_FETCH_INTERVAL_HOURS}h interval)")
                    return None
            
            if not self.client:
                logger.warning("Perplexity client not initialized")
                return None
            
            # Default comprehensive H1B/immigration query - focused on 2024-2025 updates
            if not query:
                current_year = datetime.now().year
                query = (
                    f"What are the latest H1B visa and immigration news updates for {current_year}-{current_year + 1}? "
                    f"Focus on: H1B visa policy changes {current_year}, H1B cap registration and lottery results {current_year}, "
                    f"H1B stamping appointment availability, H1B premium processing updates, "
                    f"visa bulletin priority dates for {current_year}, green card processing times, "
                    f"I-140 and I-485 filing updates, USCIS fee changes {current_year}, "
                    f"H-4 EAD work authorization news, EB-2 and EB-3 backlogs {current_year}, "
                    f"consulate visa interview experiences, new immigration regulations {current_year}. "
                    "Include only recent news from the past 14 days with official sources like USCIS.gov, "
                    "State Department, immigration law firms, and major news outlets."
                )
            
            logger.info(f"🔍 Fetching H1B news from Perplexity using SDK (query: {len(query)} chars)...")
            
            # Use official SDK without domain filter for better results
            search = self.client.search.create(
                query=query,
                max_results=max_results,
                max_tokens_per_page=2048
            )
            
            # Track successful API call
            self.last_api_fetch = datetime.now()
            
            # Extract results from SDK response
            results = []
            if hasattr(search, 'results') and search.results:
                # Debug: Log first result to see all available fields
                if len(search.results) > 0:
                    first_result = search.results[0]
                    logger.info(f"🔍 DEBUG - Available fields in result: {dir(first_result)}")
                    logger.info(f"🔍 DEBUG - Result dict: {first_result.__dict__ if hasattr(first_result, '__dict__') else 'No __dict__'}")
                
                for i, result in enumerate(search.results):
                    result_data = {
                        'title': result.title if hasattr(result, 'title') else 'Untitled',
                        'content': result.content if hasattr(result, 'content') else result.snippet if hasattr(result, 'snippet') else '',
                        'url': result.url if hasattr(result, 'url') else '#',
                        'published_date': result.published_date if hasattr(result, 'published_date') else datetime.now().isoformat(),
                        'site': result.site if hasattr(result, 'site') else 'Immigration News'
                    }
                    
                    # Check for snapshot field
                    if hasattr(result, 'snapshot'):
                        result_data['snapshot'] = result.snapshot
                        logger.info(f"📸 Found snapshot field in result {i}")
                    
                    results.append(result_data)
            
            logger.info(f"✅ Successfully fetched {len(results)} news articles from Perplexity SDK")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching news from Perplexity SDK: {e}")
            return None
    
    def _process_single_article(self, result: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """
        Process a single article (used for parallel processing)
        """
        try:
            original_title = result.get('title', f'H1B Visa News Update #{index+1}')
            perplexity_content = result.get('content', result.get('snippet', ''))
            snapshot = result.get('snapshot', '')  # Check for snapshot field
            url = result.get('url', f'https://example.com/h1b-news/{index+1}')
            published_at = result.get('published_date', datetime.now().isoformat())
            source = result.get('site', 'Immigration News')
            
            # Try to get full article content (Priority: Snapshot > Scrape > Perplexity snippet)
            if snapshot and len(snapshot) > len(perplexity_content):
                logger.info(f"📸 Using snapshot for article {index}: {len(snapshot)} chars")
                full_content = snapshot
            else:
                logger.info(f"🌐 Scraping full article {index} from URL: {url}")
                # Reduced timeout to 5s per article for faster processing
                from .article_scraper import scrape_article_content
                full_content = scrape_article_content(url, timeout=5)
                if not full_content or len(full_content) < 100:
                    logger.warning(f"⚠️  Scraping failed, using Perplexity content for article {index}")
                    full_content = perplexity_content
            
            # Generate SHORT title using Groq (with full content)
            short_title = generate_short_title(original_title, full_content)
            
            # Generate AI summary (with full content)
            ai_summary = generate_comprehensive_ai_summary(original_title, full_content)
            
            # Generate image topic for better images
            image_topic = f"{original_title} immigration visa"
            
            article = {
                "id": f"article-{index}",
                "title": short_title,
                "summary": full_content[:300] + "..." if len(full_content) > 300 else full_content,
                "content": full_content,  # Store full scraped content
                "url": url,
                "publishedAt": published_at,
                "source": source,
                "imageUrl": get_fallback_image(image_topic, index),
                "aiSummary": ai_summary,
                "tags": ["H1B", "Visa", "Immigration", "Work Visa", "Tech Industry"]
            }
            return article
            
        except Exception as e:
            logger.error(f"Error processing article {index}: {e}")
            return None
    
    def process_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process Perplexity search results in PARALLEL for faster processing
        
        Args:
            results: Raw search results from Perplexity
        
        Returns:
            Processed articles with AI summaries, images, and metadata
        """
        if not results:
            return []
        
        articles = []
        results_to_process = results[:12]  # Limit to 12 articles
        
        logger.info(f"🚀 Processing {len(results_to_process)} articles in parallel...")
        
        # Process articles in parallel using ThreadPoolExecutor (max 4 concurrent)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_index = {executor.submit(self._process_single_article, result, i): i 
                             for i, result in enumerate(results_to_process)}
            
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    article = future.result()
                    if article:
                        articles.append(article)
                        logger.info(f"✅ Completed article {index + 1}/{len(results_to_process)}")
                except Exception as e:
                    logger.error(f"❌ Failed to process article {index}: {e}")
        
        # Sort articles by original index to maintain order
        articles.sort(key=lambda x: int(x['id'].split('-')[1]))
        
        logger.info(f"✅ Successfully processed {len(articles)} articles")
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
        Get articles from MongoDB
        
        Args:
            limit: Maximum number of articles to return
        
        Returns:
            Dictionary with articles and metadata
        """
        articles = self.news_model.get_articles(limit=limit)
        latest_date = self.news_model.get_latest_article_date()
        
        cache_age_hours = 0
        if latest_date:
            cache_age_hours = round(
                (datetime.now() - latest_date).total_seconds() / 3600, 
                1
            )
        
        return {
            "articles": articles,
            "total": len(articles),
            "timestamp": latest_date.isoformat() if latest_date else datetime.now().isoformat(),
            "source": "mongodb",
            "cache_age_hours": cache_age_hours,
            "has_articles": len(articles) > 0
        }
    
    def is_cache_expired(self) -> bool:
        """Check if cache is expired"""
        if not self.cache["last_updated"]:
            return True
        
        cache_age_hours = (datetime.now() - self.cache["last_updated"]).total_seconds() / 3600
        return cache_age_hours > self.CACHE_EXPIRY_HOURS
    
    def refresh_cache(self, force: bool = False) -> Dict[str, Any]:
        """
        Refresh news from Perplexity and save to MongoDB
        
        Args:
            force: Force refresh even if recently fetched
        
        Returns:
            Result dictionary with status and message
        """
        logger.info("🔄 Refreshing news cache...")
        
        try:
            # Fetch from Perplexity using SDK
            results = self.fetch_news()
            
            if results:
                new_articles = self.process_results(results)
                if new_articles:
                    # Save to MongoDB
                    save_result = self.news_model.save_articles(new_articles)
                    
                    if save_result.get("success"):
                        logger.info(f"✅ Saved {save_result['saved']} new articles to MongoDB")
                        
                        return {
                            "success": True,
                            "message": f"Successfully saved {save_result['saved']} new articles",
                            "status": "success",
                            "saved": save_result['saved'],
                            "updated": save_result['updated'],
                            "total_in_db": self.news_model.get_article_count()
                        }
                    else:
                        return {"success": False, "message": "Failed to save to MongoDB", "status": "failed"}
                else:
                    logger.warning("No articles processed from Perplexity data")
                    return {"success": False, "message": "No articles processed", "status": "failed"}
            else:
                logger.warning("Failed to fetch from Perplexity")
                return {"success": False, "message": "Failed to fetch from Perplexity", "status": "failed"}
                
        except Exception as e:
            logger.error(f"Error refreshing cache: {e}")
            return {"success": False, "message": f"Error: {str(e)}", "status": "error"}
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get current MongoDB cache status"""
        article_count = self.news_model.get_article_count()
        latest_date = self.news_model.get_latest_article_date()
        
        cache_age_hours = 0
        if latest_date:
            cache_age_hours = round(
                (datetime.now() - latest_date).total_seconds() / 3600,
                1
            )
        
        return {
            "has_articles": article_count > 0,
            "article_count": article_count,
            "last_updated": latest_date.isoformat() if latest_date else None,
            "cache_age_hours": cache_age_hours,
            "is_expired": cache_age_hours > self.CACHE_EXPIRY_HOURS if latest_date else True,
            "perplexity_available": self.client is not None,
            "storage": "mongodb"
        }
