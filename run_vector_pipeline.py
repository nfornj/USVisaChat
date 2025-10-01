"""
Complete Vector Pipeline Runner
Integrates existing CSV processor with new vector storage
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from csv_data_processor import CSVDataProcessor
from simple_vector_processor import SimpleVectorProcessor
from vector_quality_tester import VectorQualityTester

logger = logging.getLogger(__name__)

class VectorPipelineRunner:
    """Complete pipeline from raw CSV to tested vector storage"""
    
    def __init__(self):
        self.csv_processor = CSVDataProcessor()
        self.vector_processor = SimpleVectorProcessor()
        self.tester = VectorQualityTester(self.vector_processor)
    
    async def run_complete_pipeline(self, input_csv_files: list = None) -> Dict[str, Any]:
        """Run the complete pipeline: CSV → Processing → Vectors → Testing"""
        
        logger.info("🚀 Starting Complete Vector Pipeline...")
        
        results = {
            'start_time': datetime.now().isoformat(),
            'steps': {}
        }
        
        try:
            # Step 1: Find input files if not provided
            if not input_csv_files:
                raw_dir = Path("data/conversations/raw")
                input_csv_files = list(raw_dir.glob("*.csv"))
                if not input_csv_files:
                    return {'error': 'No CSV files found in data/conversations/raw/'}
            
            logger.info(f"📁 Processing {len(input_csv_files)} CSV files")
            
            # Step 2: Initialize vector processor
            logger.info("🔧 Initializing vector processor...")
            await self.vector_processor.initialize()
            results['steps']['initialization'] = 'completed'
            
            # Step 3: Process CSV files to vectors
            logger.info("⚙️  Processing CSV files to vectors...")
            vector_results = []
            
            for csv_file in input_csv_files:
                logger.info(f"📄 Processing: {csv_file}")
                result = await self.vector_processor.process_csv_to_vectors(csv_file)
                vector_results.append(result)
            
            total_vectors = sum(r.get('vectors_created', 0) for r in vector_results)
            results['steps']['vector_creation'] = {
                'completed': True,
                'total_vectors': total_vectors,
                'files_processed': len(vector_results)
            }
            
            logger.info(f"✅ Created {total_vectors} vectors from {len(vector_results)} files")
            
            # Step 4: Test vector quality
            logger.info("🧪 Testing vector quality...")
            test_results = await self.tester.run_comprehensive_tests()
            results['steps']['quality_testing'] = test_results
            
            # Step 5: Generate summary
            overall_score = test_results.get('overall_score', 0)
            results['overall_quality_score'] = overall_score
            results['recommendation'] = self.get_recommendation(overall_score)
            
            logger.info(f"🎉 Pipeline completed! Quality score: {overall_score:.1%}")
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            results['error'] = str(e)
        
        results['end_time'] = datetime.now().isoformat()
        return results
    
    def get_recommendation(self, score: float) -> str:
        """Get recommendation based on quality score"""
        if score >= 0.8:
            return "🟢 EXCELLENT - Vector system is ready for production use"
        elif score >= 0.6:
            return "🟡 GOOD - Vector system works well, minor improvements possible"
        elif score >= 0.4:
            return "🟠 FAIR - Vector system needs improvement before production"
        else:
            return "🔴 POOR - Vector system requires significant improvements"
    
    async def quick_test_existing_vectors(self) -> Dict[str, Any]:
        """Quick test of existing vectors (skip processing)"""
        
        logger.info("⚡ Running quick test on existing vectors...")
        
        await self.vector_processor.initialize()
        
        # Check if vectors exist
        stats = await self.vector_processor.get_collection_stats()
        if stats.get('total_vectors', 0) == 0:
            return {'error': 'No vectors found. Run full pipeline first.'}
        
        # Run quick relevance test only
        test_results = await self.tester.test_relevance_quality()
        
        return {
            'collection_stats': stats,
            'relevance_test': test_results,
            'recommendation': self.get_recommendation(test_results['average_relevance'])
        }
    
    async def search_demo(self, queries: list = None) -> Dict[str, Any]:
        """Demonstrate search functionality"""
        
        if not queries:
            queries = [
                "H1B dropbox eligibility requirements",
                "F1 student visa interview experience", 
                "Processing time Mumbai consulate",
                "Emergency appointment urgent travel"
            ]
        
        logger.info("🔍 Running search demo...")
        
        await self.vector_processor.initialize()
        
        demo_results = []
        
        for query in queries:
            logger.info(f"🔍 Searching: {query}")
            
            search_results = await self.vector_processor.semantic_search(query, limit=3)
            
            demo_results.append({
                'query': query,
                'num_results': len(search_results),
                'top_results': [
                    {
                        'score': r['score'],
                        'category': r['metadata'].get('primary_category', 'unknown'),
                        'visa_type': r['metadata'].get('visa_type', 'unknown'),
                        'text_preview': r['text'][:100] + '...' if len(r['text']) > 100 else r['text']
                    }
                    for r in search_results
                ]
            })
        
        return {
            'demo_queries': len(queries),
            'results': demo_results
        }

# CLI interface
async def main():
    """Command line interface"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Complete Vector Pipeline Runner")
    parser.add_argument("--full-pipeline", action="store_true", 
                       help="Run complete pipeline: CSV → Vectors → Testing")
    parser.add_argument("--test-only", action="store_true",
                       help="Test existing vectors only")
    parser.add_argument("--demo", action="store_true",
                       help="Run search demo")
    parser.add_argument("--csv", nargs="+", type=Path,
                       help="Specific CSV files to process")
    
    args = parser.parse_args()
    
    runner = VectorPipelineRunner()
    
    try:
        if args.full_pipeline:
            # Run complete pipeline
            results = await runner.run_complete_pipeline(args.csv)
            
            print("\n" + "="*60)
            print("🚀 COMPLETE VECTOR PIPELINE RESULTS")
            print("="*60)
            
            if 'error' in results:
                print(f"❌ Pipeline failed: {results['error']}")
            else:
                # Print summary
                steps = results.get('steps', {})
                
                if 'vector_creation' in steps:
                    vc = steps['vector_creation']
                    print(f"📊 Vectors Created: {vc['total_vectors']:,}")
                    print(f"📁 Files Processed: {vc['files_processed']}")
                
                if 'quality_testing' in steps:
                    score = results.get('overall_quality_score', 0)
                    print(f"🎯 Quality Score: {score:.1%}")
                
                print(f"\n💡 Recommendation:")
                print(f"   {results.get('recommendation', 'No recommendation')}")
            
            # Save detailed results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = Path(f"data/test_results/pipeline_results_{timestamp}.json")
            results_file.parent.mkdir(exist_ok=True)
            
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"\n📄 Detailed results: {results_file}")
            
        elif args.test_only:
            # Test existing vectors
            results = await runner.quick_test_existing_vectors()
            
            if 'error' in results:
                print(f"❌ {results['error']}")
            else:
                stats = results['collection_stats']
                test = results['relevance_test']
                
                print(f"📊 Collection: {stats.get('total_vectors', 0):,} vectors")
                print(f"🎯 Relevance Score: {test['average_relevance']:.1%}")
                print(f"✅ Passed Queries: {test['passed_queries']}/{test['total_queries']}")
                print(f"\n💡 {results['recommendation']}")
                
        elif args.demo:
            # Run search demo
            results = await runner.search_demo()
            
            print("\n" + "="*60)
            print("🔍 SEARCH DEMO RESULTS")
            print("="*60)
            
            for result in results['results']:
                print(f"\n🔍 Query: {result['query']}")
                print(f"📊 Found: {result['num_results']} results")
                
                for i, r in enumerate(result['top_results'], 1):
                    print(f"  {i}. Score: {r['score']:.3f} | {r['category']} | {r['visa_type']}")
                    print(f"     {r['text_preview']}")
        
        else:
            print("Please specify --full-pipeline, --test-only, or --demo")
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())

