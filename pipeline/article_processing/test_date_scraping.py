#!/usr/bin/env python3
"""
Test script for date-ordered article scraping functionality.
Tests the scraper's ability to find and order articles by published date.
"""

import asyncio
import logging
from simplified_redbus_scraper import SimplifiedRedBusScraper
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_date_ordering():
    """Test the date-ordered scraping functionality."""
    logger.info("🧪 Testing date-ordered article scraping...")
    
    async with SimplifiedRedBusScraper() as scraper:
        # Test getting recent articles (limit to 10 for testing)
        logger.info("📅 Finding recent articles from last 2 years...")
        recent_urls = await scraper.scrape_recent_articles(max_articles=10)
        
        if not recent_urls:
            logger.error("❌ No recent articles found")
            return
        
        logger.info(f"✅ Found {len(recent_urls)} recent articles")
        
        # Test getting dates for these articles to verify ordering
        logger.info("🔍 Verifying date ordering...")
        articles_with_dates = []
        
        for i, url in enumerate(recent_urls[:5], 1):  # Check first 5 for testing
            logger.info(f"📄 Checking date for article {i}: {url}")
            article_date = await scraper.get_article_date(url)
            
            if article_date:
                articles_with_dates.append((url, article_date))
                logger.info(f"📅 Date found: {article_date.strftime('%Y-%m-%d')}")
            else:
                logger.warning(f"⚠️ No date found for: {url}")
        
        # Verify ordering (should be newest first)
        if len(articles_with_dates) >= 2:
            logger.info("🔄 Verifying date ordering (newest first)...")
            is_ordered = True
            for i in range(1, len(articles_with_dates)):
                if articles_with_dates[i-1][1] < articles_with_dates[i][1]:
                    is_ordered = False
                    logger.error(f"❌ Date ordering issue: {articles_with_dates[i-1][1]} should be >= {articles_with_dates[i][1]}")
            
            if is_ordered:
                logger.info("✅ Articles are correctly ordered by date (newest first)")
            else:
                logger.error("❌ Articles are NOT correctly ordered by date")
        
        # Show date range
        if articles_with_dates:
            dates = [date for url, date in articles_with_dates]
            earliest = min(dates)
            latest = max(dates)
            two_years_ago = datetime.now() - timedelta(days=730)
            
            logger.info(f"📊 Date range: {earliest.strftime('%Y-%m-%d')} to {latest.strftime('%Y-%m-%d')}")
            
            if earliest >= two_years_ago:
                logger.info("✅ All articles are within the last 2 years")
            else:
                logger.warning(f"⚠️ Some articles are older than 2 years (cutoff: {two_years_ago.strftime('%Y-%m-%d')})")

async def test_url_extraction():
    """Test URL extraction methods."""
    logger.info("🔍 Testing URL extraction methods...")
    
    async with SimplifiedRedBusScraper() as scraper:
        test_pages = [
            "https://redbus2us.com/sitemap.xml",
            "https://redbus2us.com/",
            "https://redbus2us.com/page/1/"
        ]
        
        for page in test_pages:
            logger.info(f"📄 Testing URL extraction from: {page}")
            urls = await scraper.extract_urls_from_page(page, max_urls=5)
            logger.info(f"✅ Found {len(urls)} URLs from {page}")
            
            # Show first few URLs
            for url in urls[:3]:
                logger.info(f"  📎 {url}")

async def main():
    """Run all tests."""
    logger.info("🚀 Starting date-ordered scraping tests...")
    
    await test_url_extraction()
    print("\n" + "="*60 + "\n")
    await test_date_ordering()
    
    logger.info("🎯 Tests completed!")

if __name__ == "__main__":
    asyncio.run(main())