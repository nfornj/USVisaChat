"""
Test Script to Compare Old vs New Prompt Engineering Performance
"""

import asyncio
import json
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from services.llm_service import LLMService
from improved_prompt_templates import ImprovedPromptTemplates

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PromptComparisonTester:
    """Test old vs new prompts on the same queries."""
    
    def __init__(self):
        self.qdrant = QdrantClient(host='localhost', port=6333)
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.llm = LLMService()
        self.improved_templates = ImprovedPromptTemplates()
        
        # Test queries that showed poor performance in validation
        self.test_cases = [
            {
                'query': 'What is the H1B fee for 2026?',
                'expected_info': ['$215', 'registration fee', 'premium processing', 'increased'],
                'category': 'fees'
            },
            {
                'query': 'When is the H1B lottery for 2026?',
                'expected_info': ['March 7th, 2025', 'March 24th, 2025', 'deadline', 'registration'],
                'category': 'dates'
            },
            {
                'query': 'What documents do I need for H1B?',
                'expected_info': ['passport', 'educational certificates', 'transcripts', 'I-20'],
                'category': 'documents'
            },
            {
                'query': 'Premium processing fee for H1B',
                'expected_info': ['$2,805', 'optional', 'expedited'],
                'category': 'fees'
            },
            {
                'query': 'H1B registration deadline 2026',
                'expected_info': ['March 24th, 2025', 'noon EST', 'registration period'],
                'category': 'dates'
            }
        ]
    
    def create_old_prompt(self, query: str, search_results: list) -> str:
        """Create the old basic prompt that showed poor performance."""
        context_pieces = []
        for result in search_results:
            title = result.payload.get('title', 'Unknown')
            text = result.payload.get('text_preview', '')[:300]
            context_pieces.append(f"Article: {title}\n{text}")
        
        context = "\n\n".join(context_pieces)
        
        return f"""Based on the following visa-related articles, answer the question accurately.

Context: {context}

Question: {query}

Answer:"""
    
    async def test_single_query(self, test_case: dict) -> dict:
        """Test a single query with both old and new prompts."""
        query = test_case['query']
        expected_info = test_case['expected_info']
        category = test_case['category']
        
        print(f"\n🔍 Testing Query: {query}")
        print(f"   Category: {category}")
        print(f"   Expected info: {', '.join(expected_info)}")
        
        # Get search results
        query_vector = self.encoder.encode(query).tolist()
        search_results = self.qdrant.search(
            collection_name="redbus2us_articles",
            query_vector=query_vector,
            limit=3
        )
        
        print(f"   Search scores: {[f'{r.score:.3f}' for r in search_results]}")
        
        # Test old prompt
        old_prompt = self.create_old_prompt(query, search_results)
        print(f"   Old prompt length: {len(old_prompt)} chars")
        
        try:
            old_response = await self.llm.generate_response(old_prompt)
            old_response_length = len(old_response)
            
            # Check how many expected info items are in old response
            old_matches = sum(1 for info in expected_info if info.lower() in old_response.lower())
            old_accuracy = old_matches / len(expected_info)
            
        except Exception as e:
            print(f"   ❌ Old prompt failed: {e}")
            old_response = ""
            old_response_length = 0
            old_accuracy = 0
        
        # Test new prompt
        new_prompt = self.improved_templates.get_optimal_prompt(query, search_results)
        print(f"   New prompt length: {len(new_prompt)} chars")
        
        try:
            new_response = await self.llm.generate_response(new_prompt)
            new_response_length = len(new_response)
            
            # Check how many expected info items are in new response
            new_matches = sum(1 for info in expected_info if info.lower() in new_response.lower())
            new_accuracy = new_matches / len(expected_info)
            
        except Exception as e:
            print(f"   ❌ New prompt failed: {e}")
            new_response = ""
            new_response_length = 0
            new_accuracy = 0
        
        # Results
        results = {
            'query': query,
            'category': category,
            'expected_info': expected_info,
            'search_scores': [r.score for r in search_results],
            'old_prompt': {
                'length': len(old_prompt),
                'response_length': old_response_length,
                'accuracy': old_accuracy,
                'matches': old_matches,
                'response': old_response[:200] + "..." if len(old_response) > 200 else old_response
            },
            'new_prompt': {
                'length': len(new_prompt),
                'response_length': new_response_length,
                'accuracy': new_accuracy,
                'matches': new_matches,
                'response': new_response[:200] + "..." if len(new_response) > 200 else new_response
            }
        }
        
        # Print comparison
        print(f"   📊 OLD: {old_matches}/{len(expected_info)} info ({old_accuracy:.1%}) | {old_response_length} chars")
        print(f"   📊 NEW: {new_matches}/{len(expected_info)} info ({new_accuracy:.1%}) | {new_response_length} chars")
        
        improvement = new_accuracy - old_accuracy
        if improvement > 0.1:
            print(f"   🟢 IMPROVED by {improvement:.1%}")
        elif improvement > 0:
            print(f"   🟡 Slight improvement: {improvement:.1%}")
        elif improvement == 0:
            print(f"   🟨 No change")
        else:
            print(f"   🔴 Regression: {improvement:.1%}")
        
        return results
    
    async def run_comparison_test(self) -> dict:
        """Run comparison test on all queries."""
        print("🚀 Starting Prompt Engineering Comparison Test")
        print("=" * 70)
        
        all_results = []
        
        for test_case in self.test_cases:
            result = await self.test_single_query(test_case)
            all_results.append(result)
            
            # Small delay between tests
            await asyncio.sleep(2)
        
        # Calculate overall statistics
        old_avg_accuracy = sum(r['old_prompt']['accuracy'] for r in all_results) / len(all_results)
        new_avg_accuracy = sum(r['new_prompt']['accuracy'] for r in all_results) / len(all_results)
        
        old_avg_length = sum(r['old_prompt']['response_length'] for r in all_results) / len(all_results)
        new_avg_length = sum(r['new_prompt']['response_length'] for r in all_results) / len(all_results)
        
        # Summary
        summary = {
            'test_results': all_results,
            'summary': {
                'total_queries': len(all_results),
                'old_avg_accuracy': old_avg_accuracy,
                'new_avg_accuracy': new_avg_accuracy,
                'accuracy_improvement': new_avg_accuracy - old_avg_accuracy,
                'old_avg_response_length': old_avg_length,
                'new_avg_response_length': new_avg_length,
                'queries_improved': sum(1 for r in all_results if r['new_prompt']['accuracy'] > r['old_prompt']['accuracy']),
                'queries_same': sum(1 for r in all_results if r['new_prompt']['accuracy'] == r['old_prompt']['accuracy']),
                'queries_worse': sum(1 for r in all_results if r['new_prompt']['accuracy'] < r['old_prompt']['accuracy'])
            }
        }
        
        return summary
    
    def print_summary(self, results: dict):
        """Print comparison summary."""
        summary = results['summary']
        
        print("\n" + "=" * 70)
        print("📊 PROMPT ENGINEERING COMPARISON RESULTS")
        print("=" * 70)
        
        print(f"\n🎯 Overall Performance:")
        print(f"   Total test queries: {summary['total_queries']}")
        print(f"   Old prompt avg accuracy: {summary['old_avg_accuracy']:.1%}")
        print(f"   New prompt avg accuracy: {summary['new_avg_accuracy']:.1%}")
        print(f"   Accuracy improvement: {summary['accuracy_improvement']:+.1%}")
        print(f"   Old avg response length: {summary['old_avg_response_length']:.0f} chars")
        print(f"   New avg response length: {summary['new_avg_response_length']:.0f} chars")
        
        print(f"\n📈 Query-by-Query Results:")
        print(f"   🟢 Improved queries: {summary['queries_improved']}/{summary['total_queries']}")
        print(f"   🟨 Same performance: {summary['queries_same']}/{summary['total_queries']}")
        print(f"   🔴 Worse performance: {summary['queries_worse']}/{summary['total_queries']}")
        
        # Category breakdown
        category_stats = {}
        for result in results['test_results']:
            category = result['category']
            if category not in category_stats:
                category_stats[category] = {'old': [], 'new': []}
            
            category_stats[category]['old'].append(result['old_prompt']['accuracy'])
            category_stats[category]['new'].append(result['new_prompt']['accuracy'])
        
        print(f"\n📋 Category Performance:")
        for category, stats in category_stats.items():
            old_avg = sum(stats['old']) / len(stats['old'])
            new_avg = sum(stats['new']) / len(stats['new'])
            improvement = new_avg - old_avg
            
            print(f"   {category.title():>10}: {old_avg:.1%} → {new_avg:.1%} ({improvement:+.1%})")
        
        # Overall assessment
        print(f"\n✅ Assessment:")
        
        if summary['accuracy_improvement'] >= 0.3:
            print("   🟢 MAJOR IMPROVEMENT: New prompts significantly better!")
        elif summary['accuracy_improvement'] >= 0.1:
            print("   🟡 GOOD IMPROVEMENT: New prompts are better")
        elif summary['accuracy_improvement'] > 0:
            print("   🟨 MINOR IMPROVEMENT: New prompts slightly better")
        elif summary['accuracy_improvement'] == 0:
            print("   🟨 NO CHANGE: Same performance")
        else:
            print("   🔴 REGRESSION: Old prompts were better")
        
        if summary['queries_improved'] >= summary['total_queries'] * 0.7:
            print("   🟢 Most queries improved with new prompts")
        elif summary['queries_improved'] >= summary['total_queries'] * 0.5:
            print("   🟡 About half the queries improved")
        else:
            print("   🔴 Most queries did not improve")
        
        print("=" * 70)


async def main():
    """Run the prompt comparison test."""
    tester = PromptComparisonTester()
    results = await tester.run_comparison_test()
    tester.print_summary(results)
    
    # Save detailed results
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"../data/prompt_comparison_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())