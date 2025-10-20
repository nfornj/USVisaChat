#!/usr/bin/env python3
"""
Data Migration Script
Converts existing article data to new simplified format while preserving all content.
"""

import asyncio
import aiofiles
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArticleDataMigrator:
    """Migrates existing article data to new simplified format."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        
        # Source directories (backup)
        self.backup_dir = self.find_latest_backup()
        self.source_raw_dir = self.backup_dir / "redbus2us_raw_backup"
        
        # Target directories (new format)
        self.target_dir = self.project_root / "data" / "redbus2us_raw"
        self.target_articles_dir = self.target_dir / "articles"
        self.target_images_dir = self.target_dir / "images"
        
        # Create target directories
        self.target_articles_dir.mkdir(parents=True, exist_ok=True)
        self.target_images_dir.mkdir(parents=True, exist_ok=True)
        
        # Migration statistics
        self.stats = {
            'total_articles_found': 0,
            'articles_migrated': 0,
            'articles_failed': 0,
            'duplicate_articles_skipped': 0,
            'start_time': datetime.now()
        }
        
        # Track processed articles to avoid duplicates
        self.processed_urls = set()
        self.processed_ids = set()
    
    def find_latest_backup(self) -> Path:
        """Find the latest backup directory."""
        backup_root = self.project_root / "data_backup"
        if not backup_root.exists():
            raise ValueError("No backup directory found! Please ensure data was backed up first.")
        
        # Find most recent backup
        backup_dirs = [d for d in backup_root.iterdir() if d.is_dir()]
        if not backup_dirs:
            raise ValueError("No backup directories found!")
        
        latest_backup = max(backup_dirs, key=lambda x: x.stat().st_mtime)
        logger.info(f"📂 Using backup from: {latest_backup}")
        return latest_backup
    
    def generate_article_id(self, url: str, published_date: Optional[str] = None) -> str:
        """Generate unique article ID from URL and date."""
        # Extract slug from URL
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p and p != 'index.html']
        slug = path_parts[-1] if path_parts else 'unknown'
        
        # Remove file extensions
        slug = re.sub(r'\.(html|htm|php)$', '', slug)
        
        # Clean slug
        slug = re.sub(r'[^a-zA-Z0-9\-_]', '_', slug)[:50]
        
        # Use published date if available, otherwise current date
        if published_date:
            try:
                if 'T' in published_date:
                    date_obj = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                else:
                    # Try to parse various date formats
                    from dateutil import parser
                    date_obj = parser.parse(published_date)
                date_str = date_obj.strftime('%Y%m%d')
            except:
                date_str = datetime.now().strftime('%Y%m%d')
        else:
            date_str = datetime.now().strftime('%Y%m%d')
        
        return f"{date_str}_{slug}"
    
    def extract_categories_and_visa_types(self, article_data: Dict) -> tuple[List[str], List[str]]:
        """Extract categories and visa types from existing article data."""
        categories = []
        visa_types = []
        
        # Get content for analysis
        content = article_data.get('content', '').lower()
        url = article_data.get('url', '').lower()
        title = article_data.get('title', '').lower()
        
        # Extract from existing fields if available
        if 'category' in article_data:
            categories.append(article_data['category'])
        if 'visa_category' in article_data:
            visa_types.append(article_data['visa_category'])
        
        # Extract from content analysis
        combined_text = f"{content} {url} {title}"
        
        # Categories based on content themes
        if any(word in combined_text for word in ['fee', 'cost', 'price', 'payment', 'dollar']):
            if 'Fees' not in categories:
                categories.append('Fees')
        if any(word in combined_text for word in ['document', 'form', 'paper', 'certificate', 'transcript']):
            if 'Documents' not in categories:
                categories.append('Documents')
        if any(word in combined_text for word in ['interview', 'appointment', 'consulate', 'embassy']):
            if 'Interview' not in categories:
                categories.append('Interview')
        if any(word in combined_text for word in ['timeline', 'process', 'step', 'procedure', 'how to']):
            if 'Process' not in categories:
                categories.append('Process')
        if any(word in combined_text for word in ['policy', 'rule', 'change', 'update', 'new']):
            if 'Policy' not in categories:
                categories.append('Policy')
        
        # Visa types
        visa_patterns = {
            'H1B': ['h1b', 'h-1b'],
            'F1': ['f1', 'f-1', 'student'],
            'H4': ['h4', 'h-4'],
            'L1': ['l1', 'l-1'],
            'B1/B2': ['b1', 'b2', 'b-1', 'b-2', 'tourist', 'visitor'],
            'Green Card': ['green card', 'permanent resident', 'pr'],
            'J1': ['j1', 'j-1', 'exchange'],
            'O1': ['o1', 'o-1', 'extraordinary']
        }
        
        for visa_type, patterns in visa_patterns.items():
            if any(pattern in combined_text for pattern in patterns):
                if visa_type not in visa_types:
                    visa_types.append(visa_type)
        
        # Default categories if none found
        if not categories:
            categories.append('General')
        if not visa_types:
            visa_types.append('General')
        
        return categories, visa_types
    
    def convert_article_to_new_format(self, article_data: Dict) -> Optional[Dict]:
        """Convert old article format to new simplified format."""
        try:
            # Essential fields that must exist
            url = article_data.get('url')
            title = article_data.get('title')
            content = article_data.get('content')
            
            if not url or not title or not content:
                logger.warning(f"⚠️ Missing essential fields for article: {title}")
                return None
            
            # Skip duplicates
            if url in self.processed_urls:
                self.stats['duplicate_articles_skipped'] += 1
                return None
            
            # Generate article ID
            published_date = article_data.get('published_date') or article_data.get('scraped_at')
            article_id = self.generate_article_id(url, published_date)
            
            # Skip if ID already exists
            if article_id in self.processed_ids:
                # Generate alternative ID with timestamp
                timestamp = datetime.now().strftime('%H%M%S')
                article_id = f"{article_id}_{timestamp}"
            
            # Extract categories and visa types
            categories, visa_types = self.extract_categories_and_visa_types(article_data)
            
            # Create new simplified structure
            new_article = {
                "article": {
                    "id": article_id,
                    "url": url,
                    "scraped_at": article_data.get('scraped_at', datetime.now().isoformat()),
                    "title": title,
                    "published_date": published_date or datetime.now().isoformat(),
                    "content": content,
                    "categories": categories,
                    "visa_types": visa_types,
                    "images": []  # Will be populated later if needed
                }
            }
            
            # Track processed items
            self.processed_urls.add(url)
            self.processed_ids.add(article_id)
            
            return new_article
            
        except Exception as e:
            logger.error(f"❌ Error converting article: {e}")
            return None
    
    async def migrate_from_json_files(self):
        """Migrate articles from individual JSON files in backup."""
        json_files = list(self.source_raw_dir.glob("*.json"))
        logger.info(f"📄 Found {len(json_files)} JSON files to process")
        
        for json_file in json_files:
            try:
                # Load the JSON file
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Handle different data structures
                if isinstance(data, list):
                    # File contains array of articles
                    for article_data in data:
                        await self.process_single_article(article_data)
                        self.stats['total_articles_found'] += 1
                elif isinstance(data, dict):
                    # Single article or nested structure
                    if 'url' in data and 'title' in data:
                        # Single article
                        await self.process_single_article(data)
                        self.stats['total_articles_found'] += 1
                    else:
                        # Might be nested structure, try to find articles
                        await self.process_nested_structure(data)
                
            except Exception as e:
                logger.error(f"❌ Error processing file {json_file}: {e}")
    
    async def process_nested_structure(self, data: Dict):
        """Process nested data structures to find articles."""
        def find_articles(obj, path=""):
            articles = []
            if isinstance(obj, dict):
                # Check if this looks like an article
                if 'url' in obj and 'title' in obj and 'content' in obj:
                    articles.append(obj)
                else:
                    # Recursively search nested objects
                    for key, value in obj.items():
                        articles.extend(find_articles(value, f"{path}.{key}"))
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    articles.extend(find_articles(item, f"{path}[{i}]"))
            return articles
        
        articles = find_articles(data)
        logger.info(f"📄 Found {len(articles)} articles in nested structure")
        
        for article_data in articles:
            await self.process_single_article(article_data)
            self.stats['total_articles_found'] += 1
    
    async def process_single_article(self, article_data: Dict):
        """Process and save a single article."""
        try:
            # Convert to new format
            new_article = self.convert_article_to_new_format(article_data)
            if not new_article:
                return
            
            # Save to new location
            article_id = new_article['article']['id']
            output_file = self.target_articles_dir / f"{article_id}.json"
            
            async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(new_article, indent=2, ensure_ascii=False))
            
            self.stats['articles_migrated'] += 1
            
            if self.stats['articles_migrated'] % 10 == 0:
                logger.info(f"✅ Migrated {self.stats['articles_migrated']} articles...")
            
        except Exception as e:
            logger.error(f"❌ Error processing article: {e}")
            self.stats['articles_failed'] += 1
    
    async def run_migration(self):
        """Run the complete migration process."""
        logger.info("🚀 Starting article data migration...")
        
        if not self.source_raw_dir.exists():
            logger.error(f"❌ Source directory not found: {self.source_raw_dir}")
            return
        
        # Migrate from JSON files
        await self.migrate_from_json_files()
        
        # Print statistics
        self.print_migration_stats()
    
    def print_migration_stats(self):
        """Print migration statistics."""
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        
        print("\n" + "="*60)
        print("📊 MIGRATION STATISTICS")
        print("="*60)
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📄 Total articles found: {self.stats['total_articles_found']}")
        print(f"✅ Articles migrated: {self.stats['articles_migrated']}")
        print(f"❌ Articles failed: {self.stats['articles_failed']}")
        print(f"⚠️  Duplicates skipped: {self.stats['duplicate_articles_skipped']}")
        print(f"📁 Output directory: {self.target_articles_dir}")
        print(f"🖼️  Images directory: {self.target_images_dir}")
        print("="*60)
        
        if self.stats['articles_migrated'] > 0:
            print("✅ Migration completed successfully!")
            print(f"📋 Migrated articles are stored as individual JSON files")
            print(f"🔍 Next step: Run the simplified scraper to download images")
        else:
            print("⚠️ No articles were migrated. Please check the source data.")

async def main():
    """Run the migration."""
    migrator = ArticleDataMigrator()
    await migrator.run_migration()

if __name__ == "__main__":
    asyncio.run(main())