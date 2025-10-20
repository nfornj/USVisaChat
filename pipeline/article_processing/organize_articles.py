"""
Organize RedBus2US articles by date, category, and visa type.
Removes duplicates and creates a structured dataset.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArticleOrganizer:
    """Organizes articles by date, category, and visa type."""
    
    def __init__(self):
        self.raw_dir = Path("data/redbus2us_raw")
        self.organized_dir = Path("data/redbus2us_organized")
        self.organized_dir.mkdir(parents=True, exist_ok=True)
        
        # Track duplicates using content hashes
        self.content_hashes: Set[str] = set()
        
        # Statistics
        self.stats = {
            'total_articles': 0,
            'duplicates_removed': 0,
            'by_year': {},
            'by_category': {},
            'by_visa_type': {}
        }
    
    def get_content_hash(self, article: Dict) -> str:
        """Generate a hash of article content to detect duplicates."""
        content = article.get('content', '')
        title = article.get('title', '')
        key_content = f"{title}\n{content}"
        return hashlib.sha256(key_content.encode()).hexdigest()
    
    def parse_date(self, date_str: str) -> Dict[str, str]:
        """Parse date string into year and month."""
        try:
            # Try various date formats
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
                    date = datetime.strptime(date_str, fmt)
                    return {
                        'year': str(date.year),
                        'month': date.strftime('%m-%B')
                    }
                except ValueError:
                    continue
            
            # If no format matches, check for year in string
            if '2024' in date_str:
                return {'year': '2024', 'month': '00-Unknown'}
            elif '2025' in date_str:
                return {'year': '2025', 'month': '00-Unknown'}
            
            return {'year': '2024', 'month': '00-Unknown'}  # Default to 2024 if unknown
            
        except Exception as e:
            logger.warning(f"⚠️ Could not parse date: {date_str} - {e}")
            return {'year': '2024', 'month': '00-Unknown'}
    
    def organize_articles(self):
        """Organize articles by date, category, and visa type."""
        # Find the most recent raw dataset
        input_files = list(self.raw_dir.glob("redbus2us_complete_*.json"))
        if not input_files:
            logger.error("❌ No raw articles found!")
            return
        
        latest_file = max(input_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"📂 Found latest raw dataset: {latest_file}")
        
        # Load raw articles
        with open(latest_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        # Initialize organized structure
        organized = {}
        
        # Process each article
        for article in articles:
            self.stats['total_articles'] += 1
            
            # Check for duplicate content
            content_hash = self.get_content_hash(article)
            if content_hash in self.content_hashes:
                self.stats['duplicates_removed'] += 1
                continue
            self.content_hashes.add(content_hash)
            
            # Get date components
            date_info = self.parse_date(article.get('published_date', ''))
            year = date_info['year']
            month = date_info['month']
            
            # Get category and visa type
            category = article.get('category', 'Uncategorized')
            visa_type = article.get('visa_category', 'General')
            
            # Update statistics
            if year not in self.stats['by_year']:
                self.stats['by_year'][year] = 0
            self.stats['by_year'][year] += 1
            
            if category not in self.stats['by_category']:
                self.stats['by_category'][category] = 0
            self.stats['by_category'][category] += 1
            
            if visa_type not in self.stats['by_visa_type']:
                self.stats['by_visa_type'][visa_type] = 0
            self.stats['by_visa_type'][visa_type] += 1
            
            # Create nested structure
            if year not in organized:
                organized[year] = {}
            if month not in organized[year]:
                organized[year][month] = {}
            if category not in organized[year][month]:
                organized[year][month][category] = {}
            if visa_type not in organized[year][month][category]:
                organized[year][month][category][visa_type] = []
            
            # Add article to structure
            organized[year][month][category][visa_type].append(article)
        
        # Save organized dataset
        self.save_organized_articles(organized)
    
    def save_organized_articles(self, organized: Dict):
        """Save organized articles and statistics."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save complete organized dataset
        complete_file = self.organized_dir / f"organized_complete_{timestamp}.json"
        with open(complete_file, 'w', encoding='utf-8') as f:
            json.dump(organized, f, indent=2, ensure_ascii=False)
        
        # Save by year
        for year in organized:
            year_file = self.organized_dir / f"organized_{year}_{timestamp}.json"
            with open(year_file, 'w', encoding='utf-8') as f:
                json.dump(organized[year], f, indent=2, ensure_ascii=False)
        
        # Save statistics
        stats_file = self.organized_dir / f"organization_stats_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        
        # Generate report
        report_file = self.organized_dir / f"organization_report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# RedBus2US Articles Organization Report\n\n")
            
            f.write("## 📊 Overall Statistics\n\n")
            f.write(f"- Total articles processed: {self.stats['total_articles']}\n")
            f.write(f"- Duplicates removed: {self.stats['duplicates_removed']}\n")
            f.write(f"- Unique articles: {self.stats['total_articles'] - self.stats['duplicates_removed']}\n\n")
            
            f.write("## 📅 Articles by Year\n\n")
            for year in sorted(self.stats['by_year'].keys()):
                f.write(f"- {year}: {self.stats['by_year'][year]} articles\n")
            f.write("\n")
            
            f.write("## 📋 Articles by Category\n\n")
            for category in sorted(self.stats['by_category'].keys()):
                f.write(f"- {category}: {self.stats['by_category'][category]} articles\n")
            f.write("\n")
            
            f.write("## 🎯 Articles by Visa Type\n\n")
            for visa_type in sorted(self.stats['by_visa_type'].keys()):
                f.write(f"- {visa_type}: {self.stats['by_visa_type'][visa_type]} articles\n")
            f.write("\n")
            
            f.write("## 📁 Generated Files\n\n")
            f.write(f"- Complete dataset: {complete_file.name}\n")
            f.write(f"- Statistics: {stats_file.name}\n")
            f.write(f"- Year-specific files: {len(organized)} files\n")
        
        logger.info("\n" + "="*80)
        logger.info("✅ Organization completed successfully!")
        logger.info(f"📊 Total processed: {self.stats['total_articles']}")
        logger.info(f"🔄 Duplicates removed: {self.stats['duplicates_removed']}")
        logger.info(f"✨ Unique articles: {self.stats['total_articles'] - self.stats['duplicates_removed']}")
        logger.info(f"📁 Data saved to: {self.organized_dir}")
        logger.info(f"📄 Report generated: {report_file}")
        logger.info("="*80)

def main():
    """Run the article organizer."""
    organizer = ArticleOrganizer()
    organizer.organize_articles()

if __name__ == "__main__":
    main()