#!/usr/bin/env python3
"""
Data Validation Script
Validates migrated article data for integrity and consistency.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set
from collections import Counter, defaultdict
from datetime import datetime
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataValidator:
    """Validates migrated article data."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.articles_dir = self.project_root / "data" / "redbus2us_raw" / "articles"
        
        # Validation results
        self.validation_results = {
            'total_articles': 0,
            'valid_articles': 0,
            'invalid_articles': 0,
            'issues': [],
            'categories_distribution': defaultdict(int),
            'visa_types_distribution': defaultdict(int),
            'date_range': {'earliest': None, 'latest': None},
            'url_duplicates': [],
            'id_duplicates': [],
            'missing_fields': defaultdict(int)
        }
        
        # Track for duplicates
        self.seen_urls = set()
        self.seen_ids = set()
        self.duplicate_urls = set()
        self.duplicate_ids = set()
    
    def validate_article_structure(self, article_data: Dict, file_path: str) -> List[str]:
        """Validate the structure of a single article."""
        issues = []
        
        # Check top-level structure
        if 'article' not in article_data:
            issues.append(f"Missing 'article' key in {file_path}")
            return issues
        
        article = article_data['article']
        
        # Required fields
        required_fields = ['id', 'url', 'scraped_at', 'title', 'published_date', 
                          'content', 'categories', 'visa_types', 'images']
        
        for field in required_fields:
            if field not in article:
                issues.append(f"Missing required field '{field}' in {file_path}")
                self.validation_results['missing_fields'][field] += 1
        
        # Field type validation
        if 'id' in article and not isinstance(article['id'], str):
            issues.append(f"Field 'id' should be string in {file_path}")
        
        if 'url' in article and not isinstance(article['url'], str):
            issues.append(f"Field 'url' should be string in {file_path}")
        
        if 'title' in article and not isinstance(article['title'], str):
            issues.append(f"Field 'title' should be string in {file_path}")
        
        if 'content' in article and not isinstance(article['content'], str):
            issues.append(f"Field 'content' should be string in {file_path}")
        
        if 'categories' in article and not isinstance(article['categories'], list):
            issues.append(f"Field 'categories' should be list in {file_path}")
        
        if 'visa_types' in article and not isinstance(article['visa_types'], list):
            issues.append(f"Field 'visa_types' should be list in {file_path}")
        
        if 'images' in article and not isinstance(article['images'], list):
            issues.append(f"Field 'images' should be list in {file_path}")
        
        # Content validation
        if 'url' in article:
            url = article['url']
            if url in self.seen_urls:
                issues.append(f"Duplicate URL found: {url} in {file_path}")
                self.duplicate_urls.add(url)
            else:
                self.seen_urls.add(url)
        
        if 'id' in article:
            article_id = article['id']
            if article_id in self.seen_ids:
                issues.append(f"Duplicate ID found: {article_id} in {file_path}")
                self.duplicate_ids.add(article_id)
            else:
                self.seen_ids.add(article_id)
        
        # Date validation
        if 'published_date' in article:
            try:
                pub_date = article['published_date']
                if 'T' in pub_date:
                    date_obj = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                else:
                    from dateutil import parser
                    date_obj = parser.parse(pub_date)
                
                # Track date range
                if self.validation_results['date_range']['earliest'] is None or date_obj < self.validation_results['date_range']['earliest']:
                    self.validation_results['date_range']['earliest'] = date_obj
                if self.validation_results['date_range']['latest'] is None or date_obj > self.validation_results['date_range']['latest']:
                    self.validation_results['date_range']['latest'] = date_obj
                    
            except Exception as e:
                issues.append(f"Invalid published_date format in {file_path}: {e}")
        
        # Content length validation
        if 'content' in article and len(article['content']) < 100:
            issues.append(f"Article content suspiciously short ({len(article['content'])} chars) in {file_path}")
        
        # Categories and visa types tracking
        if 'categories' in article:
            for category in article['categories']:
                self.validation_results['categories_distribution'][category] += 1
        
        if 'visa_types' in article:
            for visa_type in article['visa_types']:
                self.validation_results['visa_types_distribution'][visa_type] += 1
        
        return issues
    
    def validate_all_articles(self):
        """Validate all migrated articles."""
        logger.info("🔍 Starting data validation...")
        
        if not self.articles_dir.exists():
            logger.error(f"❌ Articles directory not found: {self.articles_dir}")
            return
        
        json_files = list(self.articles_dir.glob("*.json"))
        logger.info(f"📄 Found {len(json_files)} articles to validate")
        
        self.validation_results['total_articles'] = len(json_files)
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    article_data = json.load(f)
                
                issues = self.validate_article_structure(article_data, json_file.name)
                
                if issues:
                    self.validation_results['invalid_articles'] += 1
                    self.validation_results['issues'].extend(issues)
                else:
                    self.validation_results['valid_articles'] += 1
                    
            except json.JSONDecodeError as e:
                self.validation_results['invalid_articles'] += 1
                self.validation_results['issues'].append(f"JSON decode error in {json_file.name}: {e}")
            except Exception as e:
                self.validation_results['invalid_articles'] += 1
                self.validation_results['issues'].append(f"Error processing {json_file.name}: {e}")
        
        # Store duplicate information
        self.validation_results['url_duplicates'] = list(self.duplicate_urls)
        self.validation_results['id_duplicates'] = list(self.duplicate_ids)
        
        # Print validation report
        self.print_validation_report()
    
    def print_validation_report(self):
        """Print comprehensive validation report."""
        results = self.validation_results
        
        print("\\n" + "="*70)
        print("📊 DATA VALIDATION REPORT")
        print("="*70)
        
        # Overview
        print(f"📄 Total articles: {results['total_articles']}")
        print(f"✅ Valid articles: {results['valid_articles']}")
        print(f"❌ Invalid articles: {results['invalid_articles']}")
        print(f"🎯 Success rate: {(results['valid_articles'] / results['total_articles'] * 100):.1f}%")
        
        # Date range
        if results['date_range']['earliest'] and results['date_range']['latest']:
            print(f"📅 Date range: {results['date_range']['earliest'].strftime('%Y-%m-%d')} to {results['date_range']['latest'].strftime('%Y-%m-%d')}")
        
        # Categories distribution
        print(f"\\n📑 Categories Distribution (Top 10):")
        for category, count in Counter(results['categories_distribution']).most_common(10):
            print(f"   {category}: {count}")
        
        # Visa types distribution
        print(f"\\n🎫 Visa Types Distribution:")
        for visa_type, count in Counter(results['visa_types_distribution']).most_common():
            print(f"   {visa_type}: {count}")
        
        # Issues summary
        if results['issues']:
            print(f"\\n⚠️  ISSUES FOUND ({len(results['issues'])}):")
            
            # Group similar issues
            issue_counts = Counter()
            for issue in results['issues']:
                # Extract issue type (before "in filename")
                issue_type = re.sub(r' in [^\\s]+\\.json.*$', '', issue)
                issue_counts[issue_type] += 1
            
            for issue_type, count in issue_counts.most_common():
                print(f"   • {issue_type}: {count} occurrences")
            
            # Show first few specific issues as examples
            print(f"\\n📝 Sample Issues:")
            for issue in results['issues'][:5]:
                print(f"   - {issue}")
            
            if len(results['issues']) > 5:
                print(f"   ... and {len(results['issues']) - 5} more issues")
        
        # Missing fields
        if results['missing_fields']:
            print(f"\\n🔍 Missing Fields Summary:")
            for field, count in results['missing_fields'].items():
                print(f"   {field}: missing in {count} articles")
        
        # Duplicates
        if results['url_duplicates']:
            print(f"\\n🔄 Duplicate URLs: {len(results['url_duplicates'])}")
        if results['id_duplicates']:
            print(f"🔄 Duplicate IDs: {len(results['id_duplicates'])}")
        
        print("="*70)
        
        # Final assessment
        if results['valid_articles'] == results['total_articles'] and not results['issues']:
            print("🎉 ✅ ALL VALIDATION CHECKS PASSED!")
            print("📋 Data migration completed successfully with no issues.")
        elif results['valid_articles'] / results['total_articles'] > 0.95:
            print("✅ Data validation largely successful!")
            print("🔧 Minor issues found that may need attention.")
        else:
            print("⚠️ Data validation found significant issues.")
            print("🛠️ Please review and fix issues before proceeding.")
        
        print("="*70)

def main():
    """Run validation."""
    validator = DataValidator()
    validator.validate_all_articles()

if __name__ == "__main__":
    main()