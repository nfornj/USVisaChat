"""
Simple RedBus2US H1B Content Scraper
Extracts H1B visa information from redbus2us.com
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scrape_h1b_articles(max_articles=20):
    """Scrape H1B articles from RedBus2US"""
    
    base_url = "https://redbus2us.com"
    category_url = f"{base_url}/category/us-immigration-visas/h1b-visa/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    articles = []
    
    logger.info(f"🌐 Scraping H1B articles from RedBus2US...")
    logger.info(f"📍 URL: {category_url}")
    
    try:
        # Get the main H1B category page
        response = requests.get(category_url, headers=headers, timeout=15)
        if response.status_code != 200:
            logger.error(f"Failed to fetch category page: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all article elements
        article_elements = soup.find_all('article', limit=max_articles)
        
        logger.info(f"📄 Found {len(article_elements)} articles on the page")
        
        for i, article_elem in enumerate(article_elements[:max_articles], 1):
            try:
                # Extract article URL
                link_tag = article_elem.find('a', href=True)
                if not link_tag:
                    continue
                
                article_url = link_tag['href']
                
                # Extract title
                title_tag = article_elem.find('h2', class_='entry-title') or article_elem.find('h2')
                title = title_tag.get_text().strip() if title_tag else "No title"
                
                # Extract summary/excerpt
                excerpt_tag = article_elem.find('div', class_='entry-summary') or article_elem.find('p')
                excerpt = excerpt_tag.get_text().strip() if excerpt_tag else ""
                
                # Extract date
                date_tag = article_elem.find('time') or article_elem.find('span', class_='published')
                pub_date = date_tag.get_text().strip() if date_tag else "Unknown date"
                
                # Extract categories/tags
                category_tags = article_elem.find_all('a', rel='category tag')
                categories = [tag.get_text().strip() for tag in category_tags]
                
                article_data = {
                    'title': title,
                    'url': article_url,
                    'excerpt': excerpt,
                    'published_date': pub_date,
                    'categories': categories if categories else ['H1B Visa'],
                    'source': 'RedBus2US',
                    'scraped_at': datetime.now().isoformat()
                }
                
                articles.append(article_data)
                logger.info(f"✅ [{i}/{len(article_elements)}] {title[:80]}...")
                
                time.sleep(0.5)  # Be polite to the server
                
            except Exception as e:
                logger.error(f"Error processing article {i}: {e}")
                continue
        
        # Save to file
        output_file = "data/redbus2us_h1b_articles.json"
        with open(output_file, 'w') as f:
            json.dump(articles, f, indent=2)
        
        logger.info(f"\n✅ Scraped {len(articles)} H1B articles")
        logger.info(f"💾 Saved to: {output_file}")
        
        # Print summary
        logger.info(f"\n📊 Sample Articles:")
        for article in articles[:5]:
            logger.info(f"   • {article['title']}")
        
        return articles
        
    except Exception as e:
        logger.error(f"Error scraping articles: {e}")
        return []


if __name__ == "__main__":
    import os
    os.makedirs('data', exist_ok=True)
    
    articles = scrape_h1b_articles(max_articles=20)
    
    print(f"\n{'='*70}")
    print(f"✅ Scraping Complete!")
    print(f"{'='*70}")
    print(f"Total Articles: {len(articles)}")
    print(f"Output: data/redbus2us_h1b_articles.json")
    print(f"{'='*70}\n")
