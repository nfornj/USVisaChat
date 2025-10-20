#!/usr/bin/env python3
"""
Test Script: Article Summary Quality Validation
Tests article summarization quality and evaluates suitability for vector database creation.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import time

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "backend"))

from backend.services.llm_service import llm_service
from pipeline.article_processing.article_summarizer import ArticleSummarizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SummaryQualityTester:
    """Tests and evaluates article summary quality for vector database usage."""
    
    def __init__(self):
        self.project_root = project_root
        self.data_dir = self.project_root / "data"
        self.summarizer = ArticleSummarizer()
        
        # Quality metrics thresholds
        self.quality_thresholds = {
            'min_summary_length': 50,      # Minimum words in summary
            'max_summary_length': 500,     # Maximum words in summary  
            'compression_ratio_min': 0.1,  # At least 10% of original
            'compression_ratio_max': 0.8,  # At most 80% of original
            'key_info_preservation': 0.7,  # 70% of key info should be preserved
            'coherence_score': 0.8         # Minimum coherence score
        }
    
    def load_sample_articles(self, limit: int = 5) -> List[Dict]:
        """Load sample articles for testing."""
        try:
            # Try to load from organized data first
            organized_files = list(self.data_dir.glob("redbus2us_organized/organized_complete_*.json"))
            if organized_files:
                latest_file = max(organized_files, key=lambda x: x.stat().st_mtime)
                with open(latest_file, 'r', encoding='utf-8') as f:
                    organized_data = json.load(f)
                
                articles = []
                for year in organized_data:
                    for month in organized_data[year]:
                        for category in organized_data[year][month]:
                            for visa_type in organized_data[year][month][category]:
                                articles.extend(organized_data[year][month][category][visa_type])
                                if len(articles) >= limit:
                                    return articles[:limit]
                return articles
            
            # Fallback to raw data
            raw_files = list(self.data_dir.glob("redbus2us_raw/redbus2us_complete_*.json"))
            if raw_files:
                latest_file = max(raw_files, key=lambda x: x.stat().st_mtime)
                with open(latest_file, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                return raw_data[:limit]
            
            logger.error("❌ No article data found!")
            return []
            
        except Exception as e:
            logger.error(f"❌ Error loading sample articles: {e}")
            return []
    
    def extract_key_information(self, content: str) -> Dict[str, List[str]]:
        """Extract key information types from article content."""
        key_info = {
            'dates': [],
            'fees': [],
            'documents': [],
            'processes': [],
            'requirements': [],
            'deadlines': []
        }
        
        # Extract dates (various formats)
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b'
        ]
        
        for pattern in date_patterns:
            key_info['dates'].extend(re.findall(pattern, content, re.IGNORECASE))
        
        # Extract fees and amounts
        fee_patterns = [
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',
            r'\b\d+\s*(?:USD|dollars?|fees?)\b',
            r'\bfee\s*(?:of|is|:)?\s*\$?\d+',
            r'\bcost\s*(?:of|is|:)?\s*\$?\d+'
        ]
        
        for pattern in fee_patterns:
            key_info['fees'].extend(re.findall(pattern, content, re.IGNORECASE))
        
        # Extract document-related terms
        doc_keywords = ['passport', 'photo', 'form', 'certificate', 'transcript', 'diploma', 
                       'i-20', 'ds-160', 'petition', 'receipt', 'approval', 'evidence']
        for keyword in doc_keywords:
            if keyword.lower() in content.lower():
                # Extract sentences containing document keywords
                sentences = re.split(r'[.!?]+', content)
                for sentence in sentences:
                    if keyword.lower() in sentence.lower():
                        key_info['documents'].append(sentence.strip())
                        break
        
        # Extract process steps (numbered lists, bullet points)
        process_patterns = [
            r'\b(?:step\s*\d+|first|second|third|next|then|finally)[^.!?]*[.!?]',
            r'\d+\.\s*[^.!?]*[.!?]',
            r'•\s*[^.!?]*[.!?]'
        ]
        
        for pattern in process_patterns:
            key_info['processes'].extend(re.findall(pattern, content, re.IGNORECASE))
        
        return key_info
    
    def calculate_key_info_preservation(self, original_info: Dict, summary_info: Dict) -> float:
        """Calculate how much key information is preserved in summary."""
        total_preserved = 0
        total_original = 0
        
        for info_type in original_info:
            original_items = set(original_info[info_type])
            summary_items = set(summary_info[info_type])
            
            if original_items:
                preserved = len(original_items.intersection(summary_items))
                total_preserved += preserved
                total_original += len(original_items)
        
        return total_preserved / total_original if total_original > 0 else 0
    
    def calculate_coherence_score(self, summary: str) -> float:
        """Calculate coherence score based on structure and flow."""
        score = 0.0
        
        # Check for structured format (sections, bullet points)
        if re.search(r'\d+\.|•|\*|-', summary):
            score += 0.3
        
        # Check for logical flow words
        flow_words = ['first', 'second', 'then', 'next', 'finally', 'however', 'therefore', 'additionally']
        flow_count = sum(1 for word in flow_words if word.lower() in summary.lower())
        score += min(0.3, flow_count * 0.1)
        
        # Check for complete sentences
        sentences = re.split(r'[.!?]+', summary)
        complete_sentences = [s for s in sentences if len(s.strip().split()) >= 5]
        sentence_ratio = len(complete_sentences) / max(len(sentences), 1)
        score += sentence_ratio * 0.4
        
        return min(score, 1.0)
    
    async def test_single_article(self, article: Dict) -> Dict:
        """Test summary quality for a single article."""
        logger.info(f"🔍 Testing article: {article.get('title', 'No title')[:60]}...")
        
        start_time = time.time()
        
        # Generate summary
        summary_data = await self.summarizer.summarize_article(article)
        
        if not summary_data:
            return {
                'success': False,
                'error': 'Failed to generate summary',
                'article_title': article.get('title', 'No title')
            }
        
        # Calculate metrics
        original_content = article.get('content', '')
        summary_content = summary_data.get('summary', '')
        
        original_words = len(original_content.split())
        summary_words = len(summary_content.split())
        compression_ratio = summary_words / original_words if original_words > 0 else 0
        
        # Extract key information
        original_key_info = self.extract_key_information(original_content)
        summary_key_info = self.extract_key_information(summary_content)
        
        key_info_preservation = self.calculate_key_info_preservation(original_key_info, summary_key_info)
        coherence_score = self.calculate_coherence_score(summary_content)
        
        # Evaluate quality
        quality_checks = {
            'summary_length': self.quality_thresholds['min_summary_length'] <= summary_words <= self.quality_thresholds['max_summary_length'],
            'compression_ratio': self.quality_thresholds['compression_ratio_min'] <= compression_ratio <= self.quality_thresholds['compression_ratio_max'],
            'key_info_preservation': key_info_preservation >= self.quality_thresholds['key_info_preservation'],
            'coherence': coherence_score >= self.quality_thresholds['coherence_score']
        }
        
        overall_quality = sum(quality_checks.values()) / len(quality_checks)
        processing_time = time.time() - start_time
        
        return {
            'success': True,
            'article_title': article.get('title', 'No title'),
            'article_category': article.get('category', 'Unknown'),
            'original_words': original_words,
            'summary_words': summary_words,
            'compression_ratio': compression_ratio,
            'key_info_preservation': key_info_preservation,
            'coherence_score': coherence_score,
            'quality_checks': quality_checks,
            'overall_quality': overall_quality,
            'processing_time_seconds': processing_time,
            'vector_db_suitable': overall_quality >= 0.7,
            'original_content': original_content,
            'summary_content': summary_content,
            'original_key_info': original_key_info,
            'summary_key_info': summary_key_info
        }
    
    async def run_quality_tests(self, num_articles: int = 5) -> Dict:
        """Run quality tests on multiple articles."""
        logger.info(f"🚀 Starting summary quality tests on {num_articles} articles...")
        
        # Load sample articles
        articles = self.load_sample_articles(num_articles)
        if not articles:
            return {'error': 'No articles found for testing'}
        
        logger.info(f"📊 Loaded {len(articles)} articles for testing")
        
        # Test each article
        results = []
        for i, article in enumerate(articles, 1):
            logger.info(f"📝 Testing article {i}/{len(articles)}")
            result = await self.test_single_article(article)
            results.append(result)
            
            # Add delay between requests to avoid overwhelming the LLM
            await asyncio.sleep(1)
        
        # Calculate overall statistics
        successful_tests = [r for r in results if r.get('success')]
        
        if not successful_tests:
            return {'error': 'All tests failed'}
        
        avg_metrics = {
            'compression_ratio': sum(r['compression_ratio'] for r in successful_tests) / len(successful_tests),
            'key_info_preservation': sum(r['key_info_preservation'] for r in successful_tests) / len(successful_tests),
            'coherence_score': sum(r['coherence_score'] for r in successful_tests) / len(successful_tests),
            'overall_quality': sum(r['overall_quality'] for r in successful_tests) / len(successful_tests),
            'processing_time': sum(r['processing_time_seconds'] for r in successful_tests) / len(successful_tests)
        }
        
        vector_db_suitable_count = sum(1 for r in successful_tests if r['vector_db_suitable'])
        
        return {
            'total_articles_tested': len(articles),
            'successful_tests': len(successful_tests),
            'failed_tests': len(articles) - len(successful_tests),
            'average_metrics': avg_metrics,
            'vector_db_suitable_percentage': (vector_db_suitable_count / len(successful_tests)) * 100,
            'individual_results': results,
            'recommendation': self.generate_recommendation(avg_metrics, vector_db_suitable_count / len(successful_tests))
        }
    
    def generate_recommendation(self, avg_metrics: Dict, suitable_ratio: float) -> str:
        """Generate recommendation based on test results."""
        if suitable_ratio >= 0.8 and avg_metrics['overall_quality'] >= 0.8:
            return "✅ EXCELLENT: Summaries are high quality and highly suitable for vector database creation."
        elif suitable_ratio >= 0.6 and avg_metrics['overall_quality'] >= 0.7:
            return "👍 GOOD: Summaries are good quality and suitable for vector database with minor optimization."
        elif suitable_ratio >= 0.4 and avg_metrics['overall_quality'] >= 0.6:
            return "⚠️ MODERATE: Summaries need improvement. Consider adjusting prompts or LLM parameters."
        else:
            return "❌ POOR: Summaries quality is insufficient for vector database. Significant improvements needed."
    
    def print_detailed_report(self, results: Dict):
        """Print detailed test results."""
        print("\n" + "="*80)
        print("📊 ARTICLE SUMMARY QUALITY TEST REPORT")
        print("="*80)
        
        if 'error' in results:
            print(f"❌ Error: {results['error']}")
            return
        
        print(f"📈 OVERALL RESULTS:")
        print(f"   Articles Tested: {results['total_articles_tested']}")
        print(f"   Successful Tests: {results['successful_tests']}")
        print(f"   Failed Tests: {results['failed_tests']}")
        print(f"   Vector DB Suitable: {results['vector_db_suitable_percentage']:.1f}%")
        
        print(f"\n📊 AVERAGE QUALITY METRICS:")
        avg = results['average_metrics']
        print(f"   Compression Ratio: {avg['compression_ratio']:.3f}")
        print(f"   Key Info Preservation: {avg['key_info_preservation']:.3f}")
        print(f"   Coherence Score: {avg['coherence_score']:.3f}")
        print(f"   Overall Quality: {avg['overall_quality']:.3f}")
        print(f"   Avg Processing Time: {avg['processing_time']:.2f}s")
        
        print(f"\n🎯 RECOMMENDATION:")
        print(f"   {results['recommendation']}")
        
        print(f"\n📝 INDIVIDUAL RESULTS:")
        for i, result in enumerate(results['individual_results'], 1):
            if result.get('success'):
                status = "✅ SUITABLE" if result['vector_db_suitable'] else "❌ NEEDS WORK"
                print(f"   {i}. {result['article_title'][:50]}... - {status}")
                print(f"      Quality: {result['overall_quality']:.2f} | Words: {result['original_words']}→{result['summary_words']} | Time: {result['processing_time_seconds']:.1f}s")
            else:
                print(f"   {i}. FAILED: {result.get('error', 'Unknown error')}")
        
        # Show sample comparison for best result
        best_result = max([r for r in results['individual_results'] if r.get('success')], 
                         key=lambda x: x['overall_quality'], default=None)
        
        if best_result:
            print(f"\n📋 SAMPLE COMPARISON (Best Result):")
            print(f"Title: {best_result['article_title']}")
            print(f"Quality Score: {best_result['overall_quality']:.3f}")
            print(f"\nORIGINAL ({best_result['original_words']} words):")
            print(f"{best_result['original_content'][:300]}...")
            print(f"\nSUMMARY ({best_result['summary_words']} words):")
            print(f"{best_result['summary_content'][:500]}...")
        
        print("\n" + "="*80)

async def main():
    """Run the summary quality tests."""
    tester = SummaryQualityTester()
    
    print("🔍 Article Summary Quality Tester")
    print("Testing your local LLM's article summarization for vector database suitability...")
    
    try:
        # Test with 3 articles (adjustable)
        results = await tester.run_quality_tests(num_articles=3)
        tester.print_detailed_report(results)
        
        # Save results to file
        output_file = tester.project_root / "pipeline" / "logs" / f"summary_quality_test_{int(time.time())}.json"
        output_file.parent.mkdir(exist_ok=True, parents=True)
        
        with open(output_file, 'w') as f:
            # Remove large content fields for JSON storage
            clean_results = results.copy()
            if 'individual_results' in clean_results:
                for result in clean_results['individual_results']:
                    result.pop('original_content', None)
                    result.pop('summary_content', None)
                    result.pop('original_key_info', None)
                    result.pop('summary_key_info', None)
            
            json.dump(clean_results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())