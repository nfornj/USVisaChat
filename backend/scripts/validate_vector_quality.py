"""
Comprehensive Vector Database Quality Validation
Tests vector search accuracy against actual downloaded content and evaluates response quality
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from services.llm_service import LLMService

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorDatabaseValidator:
    """Validate vector database quality and accuracy."""
    
    def __init__(self):
        self.articles_dir = Path("../data/redbus2us_raw/articles")
        self.qdrant = QdrantClient(host='localhost', port=6333)
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.llm = LLMService()
        
        # Load original articles for comparison
        self.original_articles = self.load_original_articles()
        
        # Test queries organized by categories
        self.test_queries = {
            "fees": [
                "What is the H1B fee for 2026?",
                "How much does H1B cost?",
                "H1B registration fee amount",
                "Premium processing fee for H1B",
                "Total H1B visa fees breakdown"
            ],
            "timeline": [
                "When is the H1B lottery for 2026?",
                "H1B process timeline dates",
                "H1B registration deadline 2026",
                "When can I start working on H1B?",
                "H1B petition filing dates"
            ],
            "documents": [
                "What documents do I need for H1B?",
                "H1B petition requirements",
                "H1B registration documents",
                "Educational certificates for H1B",
                "Work experience documents H1B"
            ],
            "process": [
                "How does H1B lottery work?",
                "H1B visa application process",
                "Steps to apply for H1B",
                "H1B petition approval process",
                "H1B modernization rules"
            ],
            "stamping": [
                "H1B visa stamping experience",
                "H1B interview questions",
                "Visa stamping process at consulate",
                "H1B stamping documents",
                "Dropbox stamping vs interview"
            ],
            "policy": [
                "New H1B rules 2025",
                "Trump H1B fee changes",
                "H1B cap reached news",
                "H1B lottery changes",
                "USCIS H1B updates"
            ]
        }
    
    def load_original_articles(self) -> List[Dict]:
        """Load original scraped articles for comparison."""
        articles = []
        
        if not self.articles_dir.exists():
            logger.error(f"Articles directory not found: {self.articles_dir}")
            return articles
        
        for json_file in self.articles_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'article' in data:
                        articles.append(data['article'])
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")
        
        logger.info(f"Loaded {len(articles)} original articles for validation")
        return articles
    
    def calculate_content_coverage(self, query: str, search_results: List, original_articles: List[Dict]) -> Dict:
        """Calculate how well search results cover the original content."""
        
        # Find articles that should be relevant to the query
        query_lower = query.lower()
        relevant_articles = []
        
        for article in original_articles:
            title = article.get('title', '').lower()
            content = article.get('content', '').lower()
            
            # Simple relevance scoring based on keyword matching
            relevance_score = 0
            query_words = set(query_lower.split())
            
            for word in query_words:
                if len(word) > 2:  # Skip very short words
                    if word in title:
                        relevance_score += 3  # Title matches are more important
                    if word in content:
                        relevance_score += 1
            
            if relevance_score > 0:
                relevant_articles.append({
                    'article': article,
                    'relevance_score': relevance_score
                })
        
        # Sort by relevance
        relevant_articles.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Check if search results include the most relevant articles
        search_titles = [result.payload.get('title', '') for result in search_results]
        found_relevant = 0
        
        for rel_art in relevant_articles[:3]:  # Check top 3 relevant
            article_title = rel_art['article'].get('title', '')
            if any(title in article_title or article_title in title for title in search_titles):
                found_relevant += 1
        
        coverage_score = found_relevant / min(3, len(relevant_articles)) if relevant_articles else 0
        
        return {
            'total_relevant_articles': len(relevant_articles),
            'found_in_search': found_relevant,
            'coverage_score': coverage_score,
            'top_relevant_titles': [art['article'].get('title', '')[:60] + '...' 
                                   for art in relevant_articles[:3]]
        }
    
    def extract_key_facts(self, article: Dict) -> List[str]:
        """Extract key factual information from an article."""
        content = article.get('content', '')
        title = article.get('title', '')
        
        facts = []
        
        # Extract dates
        date_patterns = [
            r'(?:March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'FY\s*20\d{2}',
            r'fiscal year\s*20\d{2}'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            facts.extend([f"Date: {match}" for match in matches[:3]])  # Limit to avoid spam
        
        # Extract fees/amounts
        fee_patterns = [
            r'\$[\d,]+(?:\.\d{2})?',
            r'USD?\s*[\d,]+',
            r'fee.*?\$[\d,]+',
            r'cost.*?\$[\d,]+'
        ]
        
        for pattern in fee_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            facts.extend([f"Fee: {match}" for match in matches[:3]])
        
        # Extract quotas/numbers
        quota_patterns = [
            r'(\d{1,3},\d{3})\s*(?:visas?|applications?|registrations?)',
            r'cap.*?(\d{1,3},\d{3})',
            r'quota.*?(\d{1,3},\d{3})'
        ]
        
        for pattern in quota_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            facts.extend([f"Number: {match}" for match in matches[:2]])
        
        return facts[:10]  # Limit to 10 facts per article
    
    async def validate_response_accuracy(self, query: str, search_results: List, llm_response: str) -> Dict:
        """Validate if LLM response accurately reflects the search results."""
        
        # Extract facts from search results
        search_facts = []
        for result in search_results:
            title = result.payload.get('title', '')
            full_text = result.payload.get('full_text', '')
            
            # Create a mini article dict for fact extraction
            mini_article = {'title': title, 'content': full_text}
            facts = self.extract_key_facts(mini_article)
            search_facts.extend(facts)
        
        # Check if LLM response contains key facts
        response_lower = llm_response.lower()
        facts_mentioned = 0
        
        for fact in search_facts[:10]:  # Check top 10 facts
            fact_clean = re.sub(r'^(Date|Fee|Number):\s*', '', fact).strip()
            if len(fact_clean) > 3 and fact_clean.lower() in response_lower:
                facts_mentioned += 1
        
        accuracy_score = facts_mentioned / min(len(search_facts), 10) if search_facts else 0
        
        # Check for hallucinations (specific dates/numbers not in search results)
        potential_hallucinations = []
        
        # Look for specific dates in response
        response_dates = re.findall(r'(?:March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}', llm_response, re.IGNORECASE)
        search_text = ' '.join([result.payload.get('full_text', '') for result in search_results])
        
        for date in response_dates:
            if date not in search_text:
                potential_hallucinations.append(f"Date: {date}")
        
        # Look for specific fees in response
        response_fees = re.findall(r'\$[\d,]+(?:\.\d{2})?', llm_response)
        for fee in response_fees:
            if fee not in search_text:
                potential_hallucinations.append(f"Fee: {fee}")
        
        return {
            'total_facts_in_search': len(search_facts),
            'facts_mentioned_in_response': facts_mentioned,
            'accuracy_score': accuracy_score,
            'potential_hallucinations': potential_hallucinations,
            'hallucination_count': len(potential_hallucinations)
        }
    
    async def validate_category(self, category: str, queries: List[str]) -> Dict:
        """Validate all queries in a category."""
        category_results = {
            'category': category,
            'total_queries': len(queries),
            'results': []
        }
        
        print(f"\n📋 Validating Category: {category.upper()}")
        print("=" * 60)
        
        for i, query in enumerate(queries, 1):
            print(f"\n🔍 Query {i}/{len(queries)}: {query}")
            
            # Perform vector search
            query_vector = self.encoder.encode(query).tolist()
            search_results = self.qdrant.search(
                collection_name="redbus2us_articles",
                query_vector=query_vector,
                limit=3
            )
            
            print(f"   📊 Found {len(search_results)} results with scores:", end=" ")
            for result in search_results:
                print(f"{result.score:.3f}", end=" ")
            print()
            
            # Calculate content coverage
            coverage = self.calculate_content_coverage(query, search_results, self.original_articles)
            print(f"   📈 Content coverage: {coverage['coverage_score']:.2f} ({coverage['found_in_search']}/{coverage['total_relevant_articles']} relevant articles found)")
            
            # Generate LLM response
            context_pieces = []
            for result in search_results:
                title = result.payload.get('title', 'Unknown')
                text = result.payload.get('text_preview', '')[:300]
                context_pieces.append(f"Article: {title}\n{text}")
            
            context = "\n\n".join(context_pieces)
            prompt = f"""Based on the following visa-related articles, answer the question accurately.

Context: {context}

Question: {query}

Answer:"""
            
            try:
                llm_response = await self.llm.generate_response(prompt)
                print(f"   💬 LLM response length: {len(llm_response)} characters")
                
                # Validate response accuracy
                accuracy = await self.validate_response_accuracy(query, search_results, llm_response)
                print(f"   ✅ Accuracy score: {accuracy['accuracy_score']:.2f}")
                print(f"   ⚠️  Potential hallucinations: {accuracy['hallucination_count']}")
                
                if accuracy['potential_hallucinations']:
                    print(f"      Detected: {', '.join(accuracy['potential_hallucinations'][:2])}")
                
            except Exception as e:
                print(f"   ❌ LLM Error: {e}")
                llm_response = ""
                accuracy = {'accuracy_score': 0, 'hallucination_count': 1, 'potential_hallucinations': [str(e)]}
            
            # Store results
            query_result = {
                'query': query,
                'search_scores': [result.score for result in search_results],
                'coverage': coverage,
                'accuracy': accuracy,
                'llm_response_length': len(llm_response)
            }
            category_results['results'].append(query_result)
        
        return category_results
    
    async def run_comprehensive_validation(self) -> Dict:
        """Run comprehensive validation across all categories."""
        
        print("🚀 Starting Comprehensive Vector Database Validation")
        print("=" * 80)
        
        # Database statistics
        collection_info = self.qdrant.get_collection("redbus2us_articles")
        print(f"\n📊 Database Statistics:")
        print(f"   Collection: redbus2us_articles")
        print(f"   Total vectors: {collection_info.points_count}")
        print(f"   Vector dimensions: {collection_info.config.params.vectors.size}")
        print(f"   Original articles loaded: {len(self.original_articles)}")
        
        # Article overview
        print(f"\n📚 Article Overview:")
        for i, article in enumerate(self.original_articles[:5], 1):
            title = article.get('title', 'Unknown')[:60] + "..."
            content_length = len(article.get('content', ''))
            categories = ', '.join(article.get('categories', []))
            print(f"   {i}. {title} ({content_length:,} chars, {categories})")
        
        if len(self.original_articles) > 5:
            print(f"   ... and {len(self.original_articles) - 5} more articles")
        
        # Validate each category
        validation_results = {
            'database_stats': {
                'total_vectors': collection_info.points_count,
                'total_articles': len(self.original_articles),
                'vector_dimensions': collection_info.config.params.vectors.size
            },
            'categories': {}
        }
        
        for category, queries in self.test_queries.items():
            category_result = await self.validate_category(category, queries)
            validation_results['categories'][category] = category_result
        
        return validation_results
    
    def print_summary(self, results: Dict):
        """Print comprehensive validation summary."""
        
        print("\n" + "=" * 80)
        print("📊 VALIDATION SUMMARY")
        print("=" * 80)
        
        # Overall statistics
        total_queries = sum(len(results['categories'][cat]['results']) for cat in results['categories'])
        
        # Calculate averages
        all_scores = []
        all_coverage = []
        all_accuracy = []
        all_hallucinations = []
        
        for category in results['categories'].values():
            for result in category['results']:
                if result['search_scores']:
                    all_scores.extend(result['search_scores'])
                all_coverage.append(result['coverage']['coverage_score'])
                all_accuracy.append(result['accuracy']['accuracy_score'])
                all_hallucinations.append(result['accuracy']['hallucination_count'])
        
        avg_search_score = sum(all_scores) / len(all_scores) if all_scores else 0
        avg_coverage = sum(all_coverage) / len(all_coverage) if all_coverage else 0
        avg_accuracy = sum(all_accuracy) / len(all_accuracy) if all_accuracy else 0
        avg_hallucinations = sum(all_hallucinations) / len(all_hallucinations) if all_hallucinations else 0
        
        print(f"\n🎯 Overall Performance:")
        print(f"   Total queries tested: {total_queries}")
        print(f"   Average search score: {avg_search_score:.3f}")
        print(f"   Average content coverage: {avg_coverage:.3f}")
        print(f"   Average response accuracy: {avg_accuracy:.3f}")
        print(f"   Average hallucinations per query: {avg_hallucinations:.1f}")
        
        # Category breakdown
        print(f"\n📋 Category Performance:")
        for category, data in results['categories'].items():
            cat_scores = []
            cat_coverage = []
            cat_accuracy = []
            
            for result in data['results']:
                if result['search_scores']:
                    cat_scores.extend(result['search_scores'])
                cat_coverage.append(result['coverage']['coverage_score'])
                cat_accuracy.append(result['accuracy']['accuracy_score'])
            
            avg_cat_score = sum(cat_scores) / len(cat_scores) if cat_scores else 0
            avg_cat_coverage = sum(cat_coverage) / len(cat_coverage) if cat_coverage else 0
            avg_cat_accuracy = sum(cat_accuracy) / len(cat_accuracy) if cat_accuracy else 0
            
            print(f"   {category.title():>12}: Score {avg_cat_score:.3f} | Coverage {avg_cat_coverage:.3f} | Accuracy {avg_cat_accuracy:.3f}")
        
        # Quality assessment
        print(f"\n✅ Quality Assessment:")
        if avg_search_score >= 0.7:
            print("   🟢 Excellent semantic search quality (>0.7)")
        elif avg_search_score >= 0.5:
            print("   🟡 Good semantic search quality (0.5-0.7)")
        else:
            print("   🔴 Poor semantic search quality (<0.5)")
        
        if avg_coverage >= 0.8:
            print("   🟢 Excellent content coverage (>0.8)")
        elif avg_coverage >= 0.6:
            print("   🟡 Good content coverage (0.6-0.8)")
        else:
            print("   🔴 Poor content coverage (<0.6)")
        
        if avg_accuracy >= 0.7:
            print("   🟢 High response accuracy (>0.7)")
        elif avg_accuracy >= 0.5:
            print("   🟡 Moderate response accuracy (0.5-0.7)")
        else:
            print("   🔴 Low response accuracy (<0.5)")
        
        if avg_hallucinations <= 0.5:
            print("   🟢 Low hallucination rate (<0.5 per query)")
        elif avg_hallucinations <= 1.0:
            print("   🟡 Moderate hallucination rate (0.5-1.0 per query)")
        else:
            print("   🔴 High hallucination rate (>1.0 per query)")
        
        print("\n🚀 Vector Database Status: ", end="")
        if avg_search_score >= 0.6 and avg_coverage >= 0.7 and avg_accuracy >= 0.6:
            print("PRODUCTION READY! ✅")
        elif avg_search_score >= 0.5 and avg_coverage >= 0.5:
            print("GOOD FOR TESTING 🟡")
        else:
            print("NEEDS IMPROVEMENT 🔴")
        
        print("=" * 80)


async def main():
    """Run the validation."""
    validator = VectorDatabaseValidator()
    results = await validator.run_comprehensive_validation()
    validator.print_summary(results)
    
    # Save detailed results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = Path(f"../data/validation_results_{timestamp}.json")
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())