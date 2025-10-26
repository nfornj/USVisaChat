"""
News Model for MongoDB
Stores H1B/immigration news articles with automatic cleanup
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from models.mongodb_connection import mongodb_client

logger = logging.getLogger(__name__)


class NewsModel:
    """MongoDB model for news articles with automatic cleanup (max 20 articles)"""
    
    MAX_ARTICLES = 20
    COLLECTION_NAME = "news_articles"
    
    def __init__(self):
        """Initialize news model"""
        self.db = mongodb_client.db if mongodb_client else None
        
        # Only create collection reference if db is available
        if self.db is not None:
            self.collection = self.db[self.COLLECTION_NAME]
            self._create_indexes()
            logger.info(f"✅ News model initialized with collection: {self.COLLECTION_NAME}")
        else:
            self.collection = None
            logger.warning("⚠️  MongoDB not available - news will not be persisted")
    
    def _create_indexes(self):
        """Create indexes for efficient querying"""
        try:
            # Index on created_at (descending) for sorting by newest first
            self.collection.create_index([("created_at", -1)], name="idx_news_created_desc")
            
            # Index on url (unique) to prevent duplicates
            self.collection.create_index("url", unique=True, name="idx_news_url_unique")
            
            # Compound index for efficient querying
            self.collection.create_index(
                [("created_at", -1), ("published_at", -1)],
                name="idx_news_dates"
            )
            
            logger.info("✅ News indexes created")
        except Exception as e:
            logger.warning(f"⚠️  Index creation error (may already exist): {e}")
    
    def save_articles(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Save articles to MongoDB and maintain max 20 articles limit
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Dict with save status
        """
        if self.collection is None:
            return {"success": False, "error": "MongoDB not available"}
        
        try:
            saved_count = 0
            duplicate_count = 0
            
            for article in articles:
                try:
                    # Add created_at timestamp
                    article_data = {
                        **article,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    
                    # Upsert (update if exists, insert if new)
                    result = self.collection.update_one(
                        {"url": article.get("url")},
                        {"$set": article_data},
                        upsert=True
                    )
                    
                    if result.upserted_id:
                        saved_count += 1
                    else:
                        duplicate_count += 1
                        
                except Exception as e:
                    logger.error(f"Error saving article: {e}")
                    continue
            
            # Cleanup: Keep only the most recent MAX_ARTICLES
            self._cleanup_old_articles()
            
            return {
                "success": True,
                "saved": saved_count,
                "updated": duplicate_count,
                "total": saved_count + duplicate_count
            }
            
        except Exception as e:
            logger.error(f"Error saving articles: {e}")
            return {"success": False, "error": str(e)}
    
    def _cleanup_old_articles(self):
        """Delete articles beyond the MAX_ARTICLES limit"""
        try:
            # Count total articles
            total_count = self.collection.count_documents({})
            
            if total_count > self.MAX_ARTICLES:
                # Get the MAX_ARTICLES most recent articles
                recent_articles = list(
                    self.collection.find({}, {"_id": 1})
                    .sort("created_at", -1)
                    .limit(self.MAX_ARTICLES)
                )
                
                recent_ids = [article["_id"] for article in recent_articles]
                
                # Delete all articles not in the recent list
                delete_result = self.collection.delete_many({"_id": {"$nin": recent_ids}})
                
                if delete_result.deleted_count > 0:
                    logger.info(f"🗑️  Deleted {delete_result.deleted_count} old articles (keeping newest {self.MAX_ARTICLES})")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old articles: {e}")
    
    def get_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get articles from MongoDB (newest first)
        
        Args:
            limit: Maximum number of articles to return
            
        Returns:
            List of articles
        """
        if self.collection is None:
            return []
        
        try:
            articles = list(
                self.collection.find({}, {"_id": 0})  # Exclude MongoDB _id
                .sort("created_at", -1)
                .limit(limit)
            )
            
            logger.info(f"📰 Retrieved {len(articles)} articles from MongoDB")
            return articles
            
        except Exception as e:
            logger.error(f"Error retrieving articles: {e}")
            return []
    
    def get_article_count(self) -> int:
        """Get total number of articles in database"""
        if self.collection is None:
            return 0
        
        try:
            return self.collection.count_documents({})
        except Exception as e:
            logger.error(f"Error counting articles: {e}")
            return 0
    
    def get_latest_article_date(self) -> Optional[datetime]:
        """Get the published date of the most recent article"""
        if self.collection is None:
            return None
        
        try:
            latest = self.collection.find_one(
                {},
                {"published_at": 1},
                sort=[("published_at", -1)]
            )
            
            if latest and "published_at" in latest:
                # Handle both datetime and string formats
                pub_date = latest["published_at"]
                if isinstance(pub_date, str):
                    return datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                return pub_date
                
        except Exception as e:
            logger.error(f"Error getting latest article date: {e}")
        
        return None
    
    def clear_all(self) -> bool:
        """Clear all articles (use with caution)"""
        if self.collection is None:
            return False
        
        try:
            result = self.collection.delete_many({})
            logger.info(f"🗑️  Deleted {result.deleted_count} articles")
            return True
        except Exception as e:
            logger.error(f"Error clearing articles: {e}")
            return False


# Global instance
news_model = NewsModel()
