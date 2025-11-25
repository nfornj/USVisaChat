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
from urllib.parse import urlparse
import re

from .news_utils import (
    generate_comprehensive_ai_summary,
    generate_short_title,
    get_fallback_image
)
from .article_scraper import scrape_with_fallback
from models.news import news_model
from config.prompts import get_perplexity_news_query, get_perplexity_filters
from models.metrics import metrics_model

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
    
    def fetch_news(self, query: Optional[str] = None, max_results: int = 15, force: bool = False) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch H1B news from Perplexity Search API using official SDK
        
        Args:
            query: Custom search query (default: comprehensive H1B/immigration query)
            max_results: Maximum number of results to fetch (default: 15)
            force: If True, bypasses the 24h fetch cooldown
        
        Returns:
            List of search results or None if fetch failed
        """
        try:
            # Check rate limiting (unless forced)
            if self.last_api_fetch and not force:
                hours_since_fetch = (datetime.now() - self.last_api_fetch).total_seconds() / 3600
                if hours_since_fetch < self.MIN_FETCH_INTERVAL_HOURS:
                    logger.info(f"⏳ Perplexity API called {hours_since_fetch:.1f}h ago. Skipping (minimum {self.MIN_FETCH_INTERVAL_HOURS}h interval)")
                    return None
            
            if not self.client:
                logger.warning("Perplexity client not initialized")
                return None
            
            # Get query from environment variable or use default
            if not query:
                query = get_perplexity_news_query()
            
            logger.info(f"🔍 Fetching H1B news from Perplexity using SDK (query: {len(query)} chars)...")
            
            # Build advanced filters
            filters = get_perplexity_filters()
            # Only domain filter is supported reliably in the current Python SDK
            create_kwargs = {
                'query': query,
                'max_results': max_results,
                'max_tokens_per_page': 2048,
            }
            domains = filters.get('domains') or []
            if domains:
                # Ensure YouTube is NOT in the allowed set
                domains = [d for d in domains if 'youtube' not in d]
                create_kwargs['search_domain_filter'] = domains
            logger.info(f"🔍 Perplexity filters: domains={len(domains)}")
            
            # Use official SDK with filters
            search = self.client.search.create(**create_kwargs)
            
            # Track successful API call
            self.last_api_fetch = datetime.now()
            metrics_model.inc_perplexity()
            
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
            
            # Filter out YouTube results defensively
            def _is_youtube(u: str) -> bool:
                try:
                    host = urlparse(u).netloc.lower()
                    return any(h in host for h in ('youtube.com', 'youtu.be', 'youtube-nocookie.com', 'player.youtube.com'))
                except Exception:
                    return False
            results = [r for r in results if not _is_youtube(r.get('url', ''))]
            
            logger.info(f"✅ Successfully fetched {len(results)} non-YouTube news articles from Perplexity SDK")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching news from Perplexity SDK: {e}")
            return None
    
    def _parse_date_strict(self, date_str: Optional[str], url: str) -> Optional[datetime]:
        """Return a publication datetime only if it is parseable and within the current year.
        Falls back to parsing the URL for YYYY/MM/DD or YYYY-MM-DD. Returns None if not reliable.
        """
        def from_str(s: str) -> Optional[datetime]:
            try:
                return datetime.fromisoformat(s.replace('Z', '+00:00'))
            except Exception:
                return None
        # Try provided field
        if date_str:
            dt = from_str(str(date_str))
            if dt:
                return dt
        # Try URL patterns
        m = re.search(r"/(20\d{2})/(\d{1,2})/(\d{1,2})", url)
        if not m:
            m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", url)
        if m:
            y, mo, d = map(int, m.groups())
            try:
                return datetime(y, mo, d)
            except Exception:
                pass
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
            raw_date = result.get('published_date') or result.get('date') or result.get('published') or ''
            source = result.get('site', 'Immigration News')
            # Domain for uniqueness
            try:
                site_domain = urlparse(url).netloc.replace("www.", "")
            except Exception:
                site_domain = source.lower().replace(" ", "-")
            
            # Strict publication date handling: require parseable date in current year
            pub_dt = self._parse_date_strict(raw_date, url)
            now = datetime.now()
            if not pub_dt or pub_dt.year != now.year or (now - pub_dt).days > 30:
                logger.info(f"⏭️  Skipping article {index} due to date filter (raw='{raw_date}' url='{url}')")
                return None
            published_at = pub_dt.isoformat()
            
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
                "originalTitle": original_title,
                "summary": full_content[:300] + "..." if len(full_content) > 300 else full_content,
                "content": full_content,  # Store full scraped content
                "url": url,
                "publishedAt": published_at,
                "source": source,
                "siteDomain": site_domain,
                "topicKey": self._normalize_title(original_title),
                "sources": [{"title": original_title, "url": url, "site": source}],
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
        
        # De-duplicate by topic and merge sources
        deduped = self._dedupe_and_merge_sources(articles)
        curated = self._curate_top_articles(deduped)
        logger.info(f"✅ Successfully curated {len(curated)} articles (from {len(articles)})")
        return curated
    
    def _normalize_title(self, title: str) -> str:
        import re
        t = (title or "").lower()
        t = re.sub(r"[^a-z0-9\s]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        # Keep first 12 words as signature
        return " ".join(t.split()[:12])

    def _dedupe_and_merge_sources(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group similar articles by normalized title and merge their sources."""
        if not articles:
            return []
        groups: Dict[str, Dict[str, Any]] = {}
        for a in articles:
            key = a.get("topicKey") or self._normalize_title(a.get("originalTitle") or a.get("title"))
            if key in groups:
                # Append as additional source if url not already present
                existing = groups[key]
                urls = {s.get("url") for s in existing.get("sources", [])}
                if a.get("url") not in urls:
                    existing.setdefault("sources", []).append({
                        "title": a.get("originalTitle") or a.get("title"),
                        "url": a.get("url"),
                        "site": a.get("source")
                    })
                # Keep newest publishedAt and image
                if a.get("publishedAt", "") > existing.get("publishedAt", ""):
                    existing["publishedAt"] = a.get("publishedAt")
                if not existing.get("imageUrl") and a.get("imageUrl"):
                    existing["imageUrl"] = a.get("imageUrl")
                # Prefer explicit siteDomain
                if not existing.get("siteDomain") and a.get("siteDomain"):
                    existing["siteDomain"] = a.get("siteDomain")
            else:
                groups[key] = a
                groups[key].setdefault("sources", a.get("sources", []))
                groups[key]["topicKey"] = key
        # Return in sorted order by publishedAt desc
        unique_articles = list(groups.values())
        unique_articles.sort(key=lambda x: x.get("publishedAt", ""), reverse=True)
        return unique_articles

    def _curate_top_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply curation rules:
        - Only last 30 days
        - Prefer unique siteDomain and topicKey
        - Exactly up to 10 for display
        - Breaking news (<24h) pinned to top
        """
        if not articles:
            return []
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        # Filter by date and current year
        def parse_dt(s: str):
            try:
                return datetime.fromisoformat(str(s).replace('Z', '+00:00'))
            except Exception:
                return None
        # Keep only items with a parseable date within 30 days AND current year
        recent = []
        for a in articles:
            dt = parse_dt(a.get("publishedAt"))
            if dt and dt >= thirty_days_ago and dt.year == now.year:
                recent.append(a)
        # Sort by recency
        recent.sort(key=lambda x: x.get("publishedAt", ""), reverse=True)
        selected: List[Dict[str, Any]] = []
        seen_sites = set()
        seen_topics = set()
        # First, collect breaking news <24h regardless of repeat topic
        for a in recent:
            if len(selected) >= 10:
                break
            dt = parse_dt(a.get("publishedAt"))
            if not dt:
                continue
            age_hours = (now - dt).total_seconds() / 3600
            if age_hours <= 24 and a.get("siteDomain") not in seen_sites:
                selected.append(a)
                seen_sites.add(a.get("siteDomain"))
                seen_topics.add(a.get("topicKey"))
        # Then, fill with unique site + topic
        for a in recent:
            if len(selected) >= 10:
                break
            site = a.get("siteDomain")
            topic = a.get("topicKey")
            if site in seen_sites or topic in seen_topics:
                continue
            selected.append(a)
            seen_sites.add(site)
            seen_topics.add(topic)
        # If still less than 10, relax topic uniqueness but keep site uniqueness
        for a in recent:
            if len(selected) >= 10:
                break
            site = a.get("siteDomain")
            if site in seen_sites:
                continue
            selected.append(a)
            seen_sites.add(site)
        return selected

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
        """Check if cache is expired based on the latest article timestamp in MongoDB"""
        latest_date = self.news_model.get_latest_article_date()
        if not latest_date:
            return True
        cache_age_hours = (datetime.now() - latest_date).total_seconds() / 3600
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
            results = self.fetch_news(force=force)
            
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
