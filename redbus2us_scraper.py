"""
RedBus2US Content Scraper - Extract authoritative visa information
Scrapes articles from redbus2us.com to build official knowledge base
"""

import logging
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import List, Dict, Optional
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedBus2UScraper:
    """Scrape visa information from RedBus2US"""
    
    def __init__(self):
        self.base_url = "https://redbus2us.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.categories = {
            'H1B Visa': '/category/us-immigration-visas/h1b-visa/',
            'F1 Visa': '/category/us-immigration-visas/f1-visa/',
            'US Immigration': '/category/us-immigration-visas/',
        }
    
    def fetch_article_links(self, category_url: str, max_pages: int = 5) -> List[str]:
        """Get article links from a category"""
        article_links = []
        
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}{category_url}page/{page}/"
            
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code != 200:
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find article links
                articles = soup.find_all('article')
                for article in articles:
                    link = article.find('a')
                    if link and link.get('href'):
                        article_links.append(link['href'])
                
                logger.info(f"📄 Found {len(articles)} articles on page {page} of {category_url}")
                time.sleep(1)  # Be polite
                
            except Exception as e:
                logger.error(f"Error fetching category page {page}: {e}")
                break
        
        return list(set(article_links))  # Remove duplicates
    
    def scrape_article(self, url: str) -> Optional[Dict]:
        """Scrape a single article"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract content
            article_data = {
                'url': url,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Title
            title_tag = soup.find('h1', class_='entry-title') or soup.find('h1')
            if title_tag:
                article_data['title'] = title_tag.get_text().strip()
            
            # Date
            date_tag = soup.find('time', class_='entry-date')
            if date_tag:
                article_data['published_date'] = date_tag.get('datetime')
            
            # Content
            content_tag = soup.find('div', class_='entry-content') or soup.find('article')
            if content_tag:
                # Get all paragraphs
                paragraphs = content_tag.find_all('p')
                content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                article_data['content'] = content
                
                # Extract lists (often important info)
                lists = content_tag.find_all(['ul', 'ol'])
                list_items = []
                for lst in lists:
                    items = [li.get_text().strip() for li in lst.find_all('li')]
                    list_items.extend(items)
                article_data['key_points'] = list_items
            
            # Category/Tags
            tags = soup.find_all('a', rel='tag')
            article_data['tags'] = [tag.get_text().strip() for tag in tags]
            
            # Detect article type
            article_data['article_type'] = self.detect_article_type(article_data.get('title', ''))
            
            return article_data
            
        except Exception as e:
            logger.error(f"Error scraping article {url}: {e}")
            return None
    
    def detect_article_type(self, title: str) -> str:
        """Detect what type of information the article contains"""
        title_lower = title.lower()
        
        if 'dropbox' in title_lower:
            return 'dropbox_process'
        elif 'document' in title_lower:
            return 'documents'
        elif 'timeline' in title_lower or 'process' in title_lower:
            return 'process_timeline'
        elif 'fee' in title_lower or 'cost' in title_lower:
            return 'fees'
        elif 'interview' in title_lower:
            return 'interview'
        elif 'h1b' in title_lower:
            return 'h1b_visa'
        elif 'f1' in title_lower:
            return 'f1_visa'
        elif 'policy' in title_lower or 'rule' in title_lower or 'change' in title_lower:
            return 'policy_updates'
        else:
            return 'general_info'
    
    def scrape_all_categories(self, max_articles_per_category: int = 20) -> List[Dict]:
        """Scrape articles from all major categories"""
        all_articles = []
        
        for category_name, category_url in self.categories.items():
            logger.info(f"\n📚 Scraping category: {category_name}")
            
            # Get article links
            links = self.fetch_article_links(category_url, max_pages=2)
            logger.info(f"   Found {len(links)} articles")
            
            # Scrape articles (limit to max)
            links = links[:max_articles_per_category]
            
            for i, link in enumerate(links, 1):
                article = self.scrape_article(link)
                if article:
                    article['category'] = category_name
                    all_articles.append(article)
                    logger.info(f"   ✅ {i}/{len(links)}: {article.get('title', 'No title')[:60]}...")
                    time.sleep(1)  # Be polite to the server
        
        return all_articles
    
    def save_articles(self, articles: List[Dict], output_file: str = "data/redbus2us_articles.json"):
        """Save scraped articles"""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"\n💾 Saved {len(articles)} articles to {output_file}")
    
    def analyze_articles(self, articles: List[Dict]):
        """Analyze scraped articles"""
        stats = {
            'total_articles': len(articles),
            'by_category': {},
            'by_type': {},
            'recent_articles': 0
        }
        
        for article in articles:
            # By category
            cat = article.get('category', 'unknown')
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
            
            # By type
            atype = article.get('article_type', 'unknown')
            stats['by_type'][atype] = stats['by_type'].get(atype, 0) + 1
            
            # Recent (2025)
            pub_date = article.get('published_date', '')
            if '2025' in pub_date:
                stats['recent_articles'] += 1
        
        return stats


def main():
    """Run RedBus2US scraper"""
    scraper = RedBus2UScraper()
    
    logger.info("🌐 Starting RedBus2US Content Scraper...")
    logger.info("   Source: https://redbus2us.com")
    logger.info("="*60)
    
    # Scrape articles
    articles = scraper.scrape_all_categories(max_articles_per_category=20)
    
    # Save
    scraper.save_articles(articles)
    
    # Analyze
    stats = scraper.analyze_articles(articles)
    
    logger.info("\n" + "="*60)
    logger.info("📊 SCRAPING RESULTS")
    logger.info("="*60)
    logger.info(f"Total articles scraped: {stats['total_articles']}")
    logger.info(f"Recent articles (2025): {stats['recent_articles']}")
    logger.info(f"\n📋 By Category:")
    for cat, count in stats['by_category'].items():
        logger.info(f"  {cat}: {count}")
    logger.info(f"\n📝 By Article Type:")
    for atype, count in sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {atype}: {count}")
    logger.info("="*60)


if __name__ == "__main__":
    main()



