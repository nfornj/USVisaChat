"""
Comprehensive H1B Article Scraper - Download ALL H1B articles from RedBus2US
Batch job to build complete knowledge base
- Only scrapes articles from last 3 years
- Re-downloads updated articles
- Skips old/unchanged articles
"""

import logging
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import os
from dateutil import parser as date_parser

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ComprehensiveH1BScraper:
    """Comprehensive scraper for ALL H1B articles from RedBus2US"""
    
    def __init__(self, years_back=3):
        self.base_url = "https://redbus2us.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        # H1B specific URLs to scrape
        self.h1b_urls = [
            '/category/us-immigration-visas/h1b-visa/',
            '/category/h1b-dropbox/',
            '/category/h1b-extension/',
            '/category/h1b-transfer/',
            '/category/h1b-stamping/',
            '/category/h1b-lottery/',
            '/tag/h1b/',
        ]
        
        # Date filtering - only articles from last N years
        self.cutoff_date = datetime.now() - timedelta(days=years_back * 365)
        logger.info(f"📅 Only scraping articles published after: {self.cutoff_date.strftime('%Y-%m-%d')}")
        
        # Load existing articles to check for updates
        self.existing_articles = self.load_existing_articles()
    
    def load_existing_articles(self) -> Dict[str, Dict]:
        """Load existing articles from file to check for updates"""
        existing_file = 'data/h1b_articles_complete.json'
        
        if not os.path.exists(existing_file):
            logger.info("📄 No existing articles file found - will scrape all recent articles")
            return {}
        
        try:
            with open(existing_file, 'r') as f:
                articles = json.load(f)
            
            # Create lookup by URL
            existing_by_url = {article['url']: article for article in articles}
            logger.info(f"📚 Loaded {len(existing_by_url)} existing articles for comparison")
            return existing_by_url
        except Exception as e:
            logger.error(f"❌ Error loading existing articles: {e}")
            return {}
    
    def should_scrape_article(self, url: str, published_date: Optional[str]) -> tuple[bool, str]:
        """
        Determine if article should be scraped
        Returns: (should_scrape, reason)
        """
        # Check if article is too old
        if published_date:
            try:
                pub_date = date_parser.parse(published_date)
                if pub_date < self.cutoff_date:
                    return False, "too_old"
            except Exception as e:
                logger.warning(f"⚠️  Could not parse date '{published_date}': {e}")
        
        # Check if article exists and might need update
        if url in self.existing_articles:
            existing = self.existing_articles[url]
            existing_date = existing.get('published_date', '')
            
            # If dates match, skip (already have latest version)
            if existing_date == published_date:
                return False, "up_to_date"
            else:
                return True, "updated"
        
        # New article
        return True, "new"
    
    def fetch_all_article_links(self, category_url: str) -> List[str]:
        """Get ALL article links from a category (all pages)"""
        article_links = []
        page = 1
        
        while True:
            url = f"{self.base_url}{category_url}page/{page}/"
            
            try:
                logger.info(f"📄 Fetching page {page} of {category_url}")
                response = requests.get(url, headers=self.headers, timeout=15)
                
                if response.status_code != 200:
                    logger.info(f"✅ Reached end at page {page} (status {response.status_code})")
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find article links
                articles = soup.find_all('article')
                
                if not articles:
                    logger.info(f"✅ No more articles found at page {page}")
                    break
                
                for article in articles:
                    # Try multiple link patterns
                    link = article.find('a', class_='entry-title-link') or article.find('a')
                    if link and link.get('href'):
                        article_links.append(link['href'])
                
                logger.info(f"   Found {len(articles)} articles on page {page}")
                page += 1
                time.sleep(0.5)  # Be polite to the server
                
            except Exception as e:
                logger.error(f"❌ Error fetching page {page}: {e}")
                break
        
        return list(set(article_links))  # Remove duplicates
    
    def scrape_article(self, url: str, check_date: bool = True) -> Optional[Dict]:
        """Scrape a single article with comprehensive content extraction"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"⚠️  Failed to fetch {url} (status {response.status_code})")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract published date first to check if we should continue
            date_tag = (
                soup.find('time', class_='entry-date') or
                soup.find('time', class_='published') or
                soup.find('meta', property='article:published_time')
            )
            
            published_date = None
            if date_tag:
                published_date = date_tag.get('datetime') or date_tag.get('content') or date_tag.get_text()
            
            # Check if we should scrape this article
            if check_date:
                should_scrape, reason = self.should_scrape_article(url, published_date)
                
                if not should_scrape:
                    if reason == "too_old":
                        logger.info(f"⏭️  SKIPPING (too old): {url}")
                    elif reason == "up_to_date":
                        logger.info(f"✅ SKIPPING (up-to-date): {url}")
                    return None
                elif reason == "updated":
                    logger.info(f"🔄 RE-SCRAPING (updated): {url}")
                else:  # new
                    logger.info(f"📖 SCRAPING (new): {url}")
            
            article_data = {
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'published_date': published_date or ''
            }
            
            # Title - try multiple patterns
            title_tag = (
                soup.find('h1', class_='entry-title') or 
                soup.find('h1', class_='post-title') or
                soup.find('h1')
            )
            if title_tag:
                article_data['title'] = title_tag.get_text().strip()
            else:
                logger.warning(f"⚠️  No title found for {url}")
                return None
            
            # Category/tags
            categories = []
            category_links = soup.find_all('a', rel='category tag') or soup.find_all('a', class_='category')
            for cat in category_links:
                categories.append(cat.get_text().strip())
            article_data['category'] = ', '.join(categories) if categories else 'H1B Visa'
            
            # Tags
            tags = []
            tag_links = soup.find_all('a', rel='tag')
            for tag in tag_links:
                tags.append(tag.get_text().strip())
            article_data['tags'] = tags
            
            # Main content
            content_tag = (
                soup.find('div', class_='entry-content') or 
                soup.find('div', class_='post-content') or
                soup.find('article')
            )
            
            if content_tag:
                # Get all text content
                paragraphs = content_tag.find_all('p')
                content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                article_data['content'] = content
                
                # Extract key points from lists
                key_points = []
                lists = content_tag.find_all(['ul', 'ol'])
                for lst in lists:
                    items = [li.get_text().strip() for li in lst.find_all('li') if li.get_text().strip()]
                    key_points.extend(items)
                article_data['key_points'] = key_points
                
                # Article type detection
                title_lower = article_data['title'].lower()
                if 'lottery' in title_lower:
                    article_data['article_type'] = 'lottery'
                elif 'dropbox' in title_lower or 'stamping' in title_lower:
                    article_data['article_type'] = 'stamping'
                elif 'transfer' in title_lower:
                    article_data['article_type'] = 'transfer'
                elif 'extension' in title_lower:
                    article_data['article_type'] = 'extension'
                elif 'fee' in title_lower or 'cost' in title_lower:
                    article_data['article_type'] = 'fees'
                else:
                    article_data['article_type'] = 'general'
            
            if not article_data.get('content'):
                logger.warning(f"⚠️  No content found for {url}")
                return None
            
            # Success
            return article_data
            
        except Exception as e:
            logger.error(f"❌ Error scraping {url}: {e}")
            return None
    
    def scrape_all_h1b_articles(self) -> List[Dict]:
        """Main batch job - scrape ALL H1B articles"""
        all_links = set()
        
        # Step 1: Collect all article links
        logger.info("=" * 80)
        logger.info("🚀 STARTING COMPREHENSIVE H1B ARTICLE SCRAPING")
        logger.info("=" * 80)
        
        for category_url in self.h1b_urls:
            logger.info(f"\n📁 Processing category: {category_url}")
            links = self.fetch_all_article_links(category_url)
            all_links.update(links)
            logger.info(f"   Total unique links so far: {len(all_links)}")
            time.sleep(1)
        
        logger.info(f"\n✅ COLLECTION PHASE COMPLETE")
        logger.info(f"   Total unique articles to scrape: {len(all_links)}")
        
        # Step 2: Scrape all articles
        logger.info(f"\n📖 STARTING SCRAPING PHASE")
        articles = []
        
        for i, link in enumerate(all_links, 1):
            logger.info(f"\n[{i}/{len(all_links)}] Processing article...")
            article = self.scrape_article(link)
            
            if article:
                articles.append(article)
                
                # Save checkpoint every 50 articles
                if len(articles) % 50 == 0:
                    self.save_checkpoint(articles)
            
            time.sleep(0.5)  # Be polite
        
        logger.info(f"\n" + "=" * 80)
        logger.info(f"✅ SCRAPING COMPLETE!")
        logger.info(f"   Total articles scraped: {len(articles)}")
        logger.info(f"   Failed/skipped: {len(all_links) - len(articles)}")
        logger.info("=" * 80)
        
        return articles
    
    def save_checkpoint(self, articles: List[Dict]):
        """Save checkpoint during scraping"""
        checkpoint_file = 'data/h1b_articles_checkpoint.json'
        with open(checkpoint_file, 'w') as f:
            json.dump(articles, f, indent=2)
        logger.info(f"💾 Checkpoint saved: {len(articles)} articles")
    
    def save_articles(self, articles: List[Dict], filename: str = 'data/h1b_articles_complete.json'):
        """Save scraped articles to file"""
        os.makedirs('data', exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(articles, f, indent=2)
        
        logger.info(f"\n💾 Articles saved to: {filename}")
        logger.info(f"   Total articles: {len(articles)}")
        logger.info(f"   File size: {os.path.getsize(filename) / 1024 / 1024:.2f} MB")
        
        # Print statistics
        self.print_statistics(articles)
    
    def print_statistics(self, articles: List[Dict]):
        """Print scraping statistics"""
        logger.info(f"\n📊 SCRAPING STATISTICS")
        logger.info("=" * 80)
        
        # Count by article type
        types = {}
        for article in articles:
            article_type = article.get('article_type', 'unknown')
            types[article_type] = types.get(article_type, 0) + 1
        
        logger.info("Article Types:")
        for type_name, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {type_name}: {count}")
        
        # Date statistics
        logger.info(f"\nDate Filtering:")
        logger.info(f"  Cutoff date: {self.cutoff_date.strftime('%Y-%m-%d')}")
        logger.info(f"  Articles scraped: {len(articles)}")
        
        # Newest and oldest article
        if articles:
            dated_articles = [a for a in articles if a.get('published_date')]
            if dated_articles:
                try:
                    dates = [date_parser.parse(a['published_date']) for a in dated_articles]
                    logger.info(f"  Newest article: {max(dates).strftime('%Y-%m-%d')}")
                    logger.info(f"  Oldest article: {min(dates).strftime('%Y-%m-%d')}")
                except:
                    pass
        
        # Count articles with key points
        with_key_points = sum(1 for a in articles if a.get('key_points'))
        logger.info(f"\nArticles with key points: {with_key_points}/{len(articles)}")
        
        # Average content length
        if articles:
            avg_content_len = sum(len(a.get('content', '')) for a in articles) / len(articles)
            logger.info(f"Average content length: {avg_content_len:.0f} characters")
        
        logger.info("=" * 80)


if __name__ == "__main__":
    # Change to project root
    if os.path.exists('/app'):
        os.chdir('/app')
    elif os.path.exists('/Users/neekrish/Documents/GitHub/MyAI/Visa'):
        os.chdir('/Users/neekrish/Documents/GitHub/MyAI/Visa')
    
    scraper = ComprehensiveH1BScraper()
    articles = scraper.scrape_all_h1b_articles()
    scraper.save_articles(articles)
    
    logger.info("\n✅ BATCH SCRAPING JOB COMPLETE!")
    logger.info(f"📁 Articles saved to: data/h1b_articles_complete.json")
    logger.info(f"🚀 Ready to load into Qdrant!")

