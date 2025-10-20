"""
Comprehensive RedBus2US Content Scraper - Strategic Data Collection
Downloads all articles from last year for H1B, F1, Immigration, and General US Visa categories
Optimized for vector database training and knowledge base creation
"""

import logging
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import time
import os
from pathlib import Path
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ComprehensiveRedBus2UScraper:
    """Comprehensive scraper for strategic visa data collection"""
    
    def __init__(self):
        self.base_url = "https://redbus2us.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Comprehensive category mapping for all visa types
        self.categories = {
            'H1B Visa': '/category/us-immigration-visas/h1b-visa/',
            'F1 Visa': '/category/us-immigration-visas/f1-visa/',
            'US Immigration': '/category/us-immigration-visas/',
            'General US Visa': '/category/us-immigration-visas/visa/',
            'B1 B2 Visa': '/category/us-immigration-visas/b1-b2-visa/',
            'L1 Visa': '/category/us-immigration-visas/l1-visa/',
            'H4 Visa': '/category/us-immigration-visas/h4-visa/',
            'Green Card': '/category/us-immigration-visas/green-card/',
            'USCIS Updates': '/category/us-immigration-visas/uscis-updates/',
            'Visa Interview': '/category/us-immigration-visas/visa-interview/',
            'Dropbox': '/category/us-immigration-visas/dropbox/',
            'Visa Stamping': '/category/us-immigration-visas/visa-stamping/',
            'Policy Updates': '/category/us-immigration-visas/policy-updates/',
            'Document Requirements': '/category/us-immigration-visas/document-requirements/',
            'Timeline Process': '/category/us-immigration-visas/timeline-process/',
            'Fees Costs': '/category/us-immigration-visas/fees-costs/',
            'Visa Denial': '/category/us-immigration-visas/visa-denial/',
            'Administrative Processing': '/category/us-immigration-visas/administrative-processing/',
            'Travel Restrictions': '/category/us-immigration-visas/travel-restrictions/',
            'Embassy Updates': '/category/us-immigration-visas/embassy-updates/',
            'Latest News': '/category/us-immigration-visas/latest/',
            'Recent Updates': '/category/us-immigration-visas/updates/',
            'All Posts': '/',
            'Home': ''
        }
        
        # Date filtering for last year
        self.one_year_ago = datetime.now() - timedelta(days=365)
        self.scraped_urls: Set[str] = set()
        
        # Create data directory structure
        self.data_dir = Path("data/redbus2us_raw")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organized storage
        (self.data_dir / "articles").mkdir(exist_ok=True)
        (self.data_dir / "metadata").mkdir(exist_ok=True)
        (self.data_dir / "processed").mkdir(exist_ok=True)
    
    def is_within_last_year(self, date_str: str) -> bool:
        """Check if article is within last year"""
        if not date_str:
            return True  # Include if no date available
        
        try:
            # Parse various date formats
            date_formats = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S%z',
                '%B %d, %Y',
                '%b %d, %Y',
                '%d %B %Y',
                '%d %b %Y'
            ]
            
            for fmt in date_formats:
                try:
                    article_date = datetime.strptime(date_str, fmt)
                    return article_date >= self.one_year_ago
                except ValueError:
                    continue
            
            # If no format matches, check if it contains 2024 or 2025
            if '2024' in date_str or '2025' in date_str:
                return True
                
            return True  # Include if can't parse date
            
        except Exception:
            return True  # Include if error parsing
    
    def fetch_article_links_comprehensive(self, category_url: str, max_pages: int = 50) -> List[str]:
        """Get all article links from a category with comprehensive pagination"""
        article_links = []
        
        logger.info(f"🔍 Fetching links from {category_url} (up to {max_pages} pages)")
        
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}{category_url}page/{page}/"
            
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                if response.status_code != 200:
                    logger.warning(f"   Page {page} returned {response.status_code}, stopping")
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find article links - multiple selectors for robustness
                article_selectors = [
                    'article a[href]',
                    '.entry-title a[href]',
                    '.post-title a[href]',
                    'h2 a[href]',
                    'h3 a[href]',
                    '.article-link[href]'
                ]
                
                page_links = []
                for selector in article_selectors:
                    links = soup.select(selector)
                    for link in links:
                        href = link.get('href')
                        if href and 'redbus2us.com' in href:
                            page_links.append(href)
                
                if not page_links:
                    logger.info(f"   No more articles found on page {page}, stopping")
                    break
                
                article_links.extend(page_links)
                logger.info(f"   📄 Page {page}: Found {len(page_links)} articles")
                time.sleep(1.5)  # Be polite to server
                
            except Exception as e:
                logger.error(f"   Error fetching page {page}: {e}")
                break
        
        # Remove duplicates and filter
        unique_links = list(set(article_links))
        logger.info(f"   ✅ Total unique links found: {len(unique_links)}")
        return unique_links
    
    def scrape_article_comprehensive(self, url: str) -> Optional[Dict]:
        """Scrape a single article with comprehensive data extraction"""
        if url in self.scraped_urls:
            return None
            
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract comprehensive article data
            article_data = {
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'source': 'RedBus2US',
                'domain': 'redbus2us.com'
            }
            
            # Title
            title_selectors = [
                'h1.entry-title',
                'h1.post-title',
                'h1.article-title',
                'h1',
                '.entry-title',
                '.post-title'
            ]
            
            for selector in title_selectors:
                title_tag = soup.select_one(selector)
                if title_tag:
                    article_data['title'] = title_tag.get_text().strip()
                    break
            
            # Published date
            date_selectors = [
                'time.entry-date',
                '.entry-date',
                '.post-date',
                '.published-date',
                'time[datetime]',
                '.date'
            ]
            
            for selector in date_selectors:
                date_tag = soup.select_one(selector)
                if date_tag:
                    article_data['published_date'] = date_tag.get('datetime') or date_tag.get_text().strip()
                    break
            
            # Check if within last year
            if not self.is_within_last_year(article_data.get('published_date', '')):
                logger.debug(f"   ⏰ Article too old, skipping: {url}")
                return None
            
            # Content extraction
            content_selectors = [
                '.entry-content',
                '.post-content',
                '.article-content',
                '.content',
                'article',
                '.entry-body'
            ]
            
            content_text = ""
            key_points = []
            
            for selector in content_selectors:
                content_tag = soup.select_one(selector)
                if content_tag:
                    # Extract paragraphs
                    paragraphs = content_tag.find_all('p')
                    content_text = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                    
                    # Extract lists (bullet points, numbered lists)
                    lists = content_tag.find_all(['ul', 'ol'])
                    for lst in lists:
                        items = [li.get_text().strip() for li in lst.find_all('li')]
                        key_points.extend(items)
                    
                    # Extract headings for structure
                    headings = content_tag.find_all(['h2', 'h3', 'h4', 'h5', 'h6'])
                    heading_text = [h.get_text().strip() for h in headings]
                    
                    if heading_text:
                        article_data['headings'] = heading_text
                    
                    break
            
            article_data['content'] = content_text
            article_data['key_points'] = key_points
            
            # Extract tags and categories
            tag_selectors = [
                'a[rel="tag"]',
                '.tags a',
                '.post-tags a',
                '.article-tags a'
            ]
            
            tags = []
            for selector in tag_selectors:
                tag_elements = soup.select(selector)
                tags.extend([tag.get_text().strip() for tag in tag_elements])
            
            article_data['tags'] = list(set(tags))
            
            # Detect article type and visa category
            article_data['article_type'] = self.detect_article_type(article_data.get('title', ''))
            article_data['visa_category'] = self.detect_visa_category(article_data.get('title', ''), content_text)
            
            # Extract important entities
            article_data['entities'] = self.extract_entities(content_text)
            
            # Calculate content metrics
            article_data['word_count'] = len(content_text.split())
            article_data['key_points_count'] = len(key_points)
            article_data['has_timeline'] = 'timeline' in content_text.lower() or 'process' in content_text.lower()
            article_data['has_fees'] = 'fee' in content_text.lower() or 'cost' in content_text.lower()
            article_data['has_documents'] = 'document' in content_text.lower() or 'requirement' in content_text.lower()
            
            # Mark as scraped
            self.scraped_urls.add(url)
            
            return article_data
            
        except Exception as e:
            logger.error(f"Error scraping article {url}: {e}")
            return None
    
    def detect_article_type(self, title: str) -> str:
        """Enhanced article type detection"""
        title_lower = title.lower()
        
        type_mapping = {
            'dropbox_process': ['dropbox', 'stamping'],
            'documents': ['document', 'requirement', 'checklist'],
            'process_timeline': ['timeline', 'process', 'step', 'procedure'],
            'fees': ['fee', 'cost', 'price', 'payment'],
            'interview': ['interview', 'question', 'preparation'],
            'h1b_visa': ['h1b', 'h-1b'],
            'f1_visa': ['f1', 'f-1', 'student'],
            'b1_b2_visa': ['b1', 'b2', 'b-1', 'b-2', 'tourist', 'business'],
            'l1_visa': ['l1', 'l-1', 'intracompany'],
            'h4_visa': ['h4', 'h-4', 'dependent'],
            'green_card': ['green card', 'permanent', 'pr'],
            'policy_updates': ['policy', 'rule', 'change', 'update', 'new'],
            'visa_denial': ['denial', 'reject', 'refuse', '221g'],
            'administrative_processing': ['administrative', 'ap', 'processing'],
            'travel_restrictions': ['travel', 'restriction', 'ban', 'covid'],
            'embassy_updates': ['embassy', 'consulate', 'closure'],
            'general_info': []
        }
        
        for article_type, keywords in type_mapping.items():
            if any(keyword in title_lower for keyword in keywords):
                return article_type
        
        return 'general_info'
    
    def detect_visa_category(self, title: str, content: str) -> str:
        """Detect primary visa category"""
        text = (title + ' ' + content).lower()
        
        if 'h1b' in text or 'h-1b' in text:
            return 'H1B'
        elif 'f1' in text or 'f-1' in text or 'student' in text:
            return 'F1'
        elif 'b1' in text or 'b2' in text or 'b-1' in text or 'b-2' in text:
            return 'B1/B2'
        elif 'l1' in text or 'l-1' in text:
            return 'L1'
        elif 'h4' in text or 'h-4' in text:
            return 'H4'
        elif 'green card' in text or 'permanent' in text:
            return 'Green Card'
        else:
            return 'General'
    
    def extract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract important entities from content"""
        entities = {
            'fees': [],
            'timelines': [],
            'documents': [],
            'websites': [],
            'phone_numbers': [],
            'addresses': []
        }
        
        # Extract fees (dollar amounts)
        fee_pattern = r'\$[\d,]+(?:\.\d{2})?'
        entities['fees'] = re.findall(fee_pattern, content)
        
        # Extract timelines (time periods)
        timeline_pattern = r'\d+\s+(?:days?|weeks?|months?|years?)'
        entities['timelines'] = re.findall(timeline_pattern, content, re.IGNORECASE)
        
        # Extract documents (common document types)
        doc_pattern = r'\b(?:passport|visa|i-94|i-797|ds-160|ds-260|i-140|i-485|i-765|i-131|ead|ap|h1b|f1|b1|b2|l1|h4)\b'
        entities['documents'] = re.findall(doc_pattern, content, re.IGNORECASE)
        
        # Extract websites
        url_pattern = r'https?://[^\s]+'
        entities['websites'] = re.findall(url_pattern, content)
        
        return entities
    
    def scrape_all_categories_comprehensive(self) -> List[Dict]:
        """Scrape all categories comprehensively"""
        all_articles = []
        category_stats = {}
        
        logger.info(f"🚀 Starting comprehensive scraping for {len(self.categories)} categories")
        logger.info(f"📅 Date filter: Last year (since {self.one_year_ago.strftime('%Y-%m-%d')})")
        logger.info("="*80)
        
        for category_name, category_url in self.categories.items():
            logger.info(f"\n📚 Scraping category: {category_name}")
            logger.info(f"   URL: {self.base_url}{category_url}")
            
            try:
                # Get all article links
                links = self.fetch_article_links_comprehensive(category_url, max_pages=15)
                logger.info(f"   Found {len(links)} potential articles")
                
                # Scrape articles
                category_articles = []
                for i, link in enumerate(links, 1):
                    article = self.scrape_article_comprehensive(link)
                    if article:
                        article['category'] = category_name
                        category_articles.append(article)
                        logger.info(f"   ✅ {i}/{len(links)}: {article.get('title', 'No title')[:60]}...")
                    
                    time.sleep(1.2)  # Be polite to server
                
                all_articles.extend(category_articles)
                category_stats[category_name] = len(category_articles)
                logger.info(f"   📊 Scraped {len(category_articles)} articles from {category_name}")
                
            except Exception as e:
                logger.error(f"   ❌ Error scraping {category_name}: {e}")
                category_stats[category_name] = 0
        
        logger.info(f"\n📈 Category Statistics:")
        for cat, count in category_stats.items():
            logger.info(f"   {cat}: {count} articles")
        
        return all_articles
    
    def save_articles_strategic(self, articles: List[Dict]):
        """Save articles in strategic format for vector training"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save complete dataset
        complete_file = self.data_dir / f"redbus2us_complete_{timestamp}.json"
        with open(complete_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False, default=str)
        
        # Save by category
        for category in set(article.get('category', 'Unknown') for article in articles):
            category_articles = [a for a in articles if a.get('category') == category]
            category_file = self.data_dir / f"redbus2us_{category.lower().replace(' ', '_')}_{timestamp}.json"
            with open(category_file, 'w', encoding='utf-8') as f:
                json.dump(category_articles, f, indent=2, ensure_ascii=False, default=str)
        
        # Save by article type
        for article_type in set(article.get('article_type', 'unknown') for article in articles):
            type_articles = [a for a in articles if a.get('article_type') == article_type]
            type_file = self.data_dir / f"redbus2us_{article_type}_{timestamp}.json"
            with open(type_file, 'w', encoding='utf-8') as f:
                json.dump(type_articles, f, indent=2, ensure_ascii=False, default=str)
        
        # Save metadata summary
        metadata = {
            'scraping_timestamp': timestamp,
            'total_articles': len(articles),
            'date_range': {
                'start': self.one_year_ago.isoformat(),
                'end': datetime.now().isoformat()
            },
            'categories': list(set(article.get('category', 'Unknown') for article in articles)),
            'article_types': list(set(article.get('article_type', 'unknown') for article in articles)),
            'visa_categories': list(set(article.get('visa_category', 'General') for article in articles)),
            'total_word_count': sum(article.get('word_count', 0) for article in articles),
            'articles_with_timelines': sum(1 for a in articles if a.get('has_timeline', False)),
            'articles_with_fees': sum(1 for a in articles if a.get('has_fees', False)),
            'articles_with_documents': sum(1 for a in articles if a.get('has_documents', False))
        }
        
        metadata_file = self.data_dir / f"metadata_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"\n💾 Strategic data saved:")
        logger.info(f"   Complete dataset: {complete_file}")
        logger.info(f"   Metadata: {metadata_file}")
        logger.info(f"   Category files: {len(set(article.get('category', 'Unknown') for article in articles))}")
        logger.info(f"   Type files: {len(set(article.get('article_type', 'unknown') for article in articles))}")
    
    def analyze_comprehensive(self, articles: List[Dict]) -> Dict:
        """Comprehensive analysis of scraped articles"""
        stats = {
            'total_articles': len(articles),
            'by_category': {},
            'by_article_type': {},
            'by_visa_category': {},
            'recent_articles': 0,
            'content_metrics': {
                'total_word_count': 0,
                'avg_word_count': 0,
                'articles_with_timelines': 0,
                'articles_with_fees': 0,
                'articles_with_documents': 0
            },
            'quality_indicators': {
                'high_quality_articles': 0,
                'comprehensive_articles': 0,
                'recent_policy_updates': 0
            }
        }
        
        for article in articles:
            # Category analysis
            cat = article.get('category', 'Unknown')
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
            
            # Article type analysis
            atype = article.get('article_type', 'unknown')
            stats['by_article_type'][atype] = stats['by_article_type'].get(atype, 0) + 1
            
            # Visa category analysis
            vcat = article.get('visa_category', 'General')
            stats['by_visa_category'][vcat] = stats['by_visa_category'].get(vcat, 0) + 1
            
            # Recent articles
            pub_date = article.get('published_date', '')
            if '2024' in pub_date or '2025' in pub_date:
                stats['recent_articles'] += 1
            
            # Content metrics
            word_count = article.get('word_count', 0)
            stats['content_metrics']['total_word_count'] += word_count
            
            if article.get('has_timeline', False):
                stats['content_metrics']['articles_with_timelines'] += 1
            if article.get('has_fees', False):
                stats['content_metrics']['articles_with_fees'] += 1
            if article.get('has_documents', False):
                stats['content_metrics']['articles_with_documents'] += 1
            
            # Quality indicators
            if word_count > 1000 and article.get('key_points_count', 0) > 5:
                stats['quality_indicators']['high_quality_articles'] += 1
            
            if word_count > 2000 and article.get('key_points_count', 0) > 10:
                stats['quality_indicators']['comprehensive_articles'] += 1
            
            if 'policy' in atype or 'update' in atype:
                stats['quality_indicators']['recent_policy_updates'] += 1
        
        # Calculate averages
        if stats['total_articles'] > 0:
            stats['content_metrics']['avg_word_count'] = stats['content_metrics']['total_word_count'] / stats['total_articles']
        
        return stats


def main():
    """Run comprehensive RedBus2US scraper"""
    scraper = ComprehensiveRedBus2UScraper()
    
    logger.info("🌐 Starting Comprehensive RedBus2US Content Scraper")
    logger.info("   Source: https://redbus2us.com")
    logger.info("   Target: Last 1 year of articles")
    logger.info("   Categories: H1B, F1, Immigration, General US Visa + 16 more")
    logger.info("   Purpose: Strategic vector database training data")
    logger.info("="*80)
    
    # Scrape all categories
    articles = scraper.scrape_all_categories_comprehensive()
    
    # Save strategically
    scraper.save_articles_strategic(articles)
    
    # Analyze results
    stats = scraper.analyze_comprehensive(articles)
    
    # Print comprehensive results
    logger.info("\n" + "="*80)
    logger.info("📊 COMPREHENSIVE SCRAPING RESULTS")
    logger.info("="*80)
    logger.info(f"Total articles scraped: {stats['total_articles']}")
    logger.info(f"Recent articles (2024-2025): {stats['recent_articles']}")
    logger.info(f"Total word count: {stats['content_metrics']['total_word_count']:,}")
    logger.info(f"Average word count: {stats['content_metrics']['avg_word_count']:.0f}")
    
    logger.info(f"\n📋 By Category:")
    for cat, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {cat}: {count}")
    
    logger.info(f"\n📝 By Article Type:")
    for atype, count in sorted(stats['by_article_type'].items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {atype}: {count}")
    
    logger.info(f"\n🎯 By Visa Category:")
    for vcat, count in sorted(stats['by_visa_category'].items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {vcat}: {count}")
    
    logger.info(f"\n📊 Content Quality:")
    logger.info(f"  Articles with timelines: {stats['content_metrics']['articles_with_timelines']}")
    logger.info(f"  Articles with fees: {stats['content_metrics']['articles_with_fees']}")
    logger.info(f"  Articles with documents: {stats['content_metrics']['articles_with_documents']}")
    logger.info(f"  High quality articles: {stats['quality_indicators']['high_quality_articles']}")
    logger.info(f"  Comprehensive articles: {stats['quality_indicators']['comprehensive_articles']}")
    logger.info(f"  Policy updates: {stats['quality_indicators']['recent_policy_updates']}")
    
    logger.info("="*80)
    logger.info("✅ Comprehensive scraping completed successfully!")
    logger.info(f"📁 Data saved to: {scraper.data_dir}")


if __name__ == "__main__":
    main()
