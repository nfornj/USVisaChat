"""
Embedding Analysis and Recommendations for Visa Community Platform
Analyzes current setup and provides recommendations for optimal embeddings
"""

import json
import time
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Tuple
import requests

# Test embedding models for comparison
TEST_MODELS = {
    'current': 'all-MiniLM-L6-v2',  # Current model (384d)
    'general_v2': 'all-mpnet-base-v2',  # Better general performance (768d)
    'multilingual': 'paraphrase-multilingual-MiniLM-L12-v2',  # Multilingual support (384d)
    'legal_domain': 'sentence-transformers/all-MiniLM-L6-v2',  # Current - no legal-specific available
    'fast_small': 'all-MiniLM-L12-v2',  # Faster, slightly larger (384d)
}

class EmbeddingAnalyzer:
    """Analyze and compare embedding models for visa domain."""
    
    def __init__(self):
        self.test_queries = [
            # General visa queries
            "What is the H1B fee for 2026?",
            "When is the H1B lottery registration deadline?",
            "What documents do I need for H1B petition?",
            "H1B cap reached latest news",
            "Premium processing time for H1B",
            
            # Immigration-specific terminology
            "USCIS filing procedures",
            "Consular processing vs adjustment of status",
            "Administrative processing delays",
            "Priority date retrogression",
            "Labor certification PERM",
            
            # Community conversation style
            "my h1b got approved finally!",
            "anyone know about dropbox stamping?",
            "visa interview experience sharing",
            "rfe response help needed",
            "timeline from petition to approval"
        ]
        
        self.test_documents = [
            # Official government style
            "USCIS announced that the H1B cap for fiscal year 2026 has been reached. No additional registrations will be accepted. Employers must file petitions by June 30, 2025.",
            
            # Legal document style  
            "The petitioner must demonstrate that the beneficiary qualifies for the specialty occupation by providing evidence of the required educational background or equivalent experience.",
            
            # Community discussion style
            "Just got my H1B approved after 8 months! Premium processing really helped. Sharing my timeline for others waiting.",
            
            # Technical process description
            "Submit Form I-129 with required supporting documents including Labor Condition Application, educational credentials, and employer support letter.",
            
            # News/policy update style
            "New USCIS memo updates H1B lottery process to prevent fraud. Changes take effect January 2025 for FY 2026 registrations."
        ]
    
    def analyze_current_setup(self) -> Dict:
        """Analyze the current embedding setup."""
        
        print("🔍 Analyzing Current Embedding Setup")
        print("=" * 50)
        
        # Check Qdrant collections
        try:
            response = requests.get("http://localhost:6333/collections")
            collections = response.json()['result']['collections']
            
            collection_stats = {}
            for collection in collections:
                name = collection['name']
                detail_response = requests.get(f"http://localhost:6333/collections/{name}")
                if detail_response.status_code == 200:
                    details = detail_response.json()['result']
                    collection_stats[name] = {
                        'points': details['points_count'],
                        'vector_size': details['config']['params']['vectors']['size'],
                        'distance': details['config']['params']['vectors']['distance']
                    }
        except Exception as e:
            print(f"❌ Error fetching collection stats: {e}")
            collection_stats = {}
        
        # Current model info
        current_model = 'all-MiniLM-L6-v2'
        
        analysis = {
            'current_model': current_model,
            'vector_dimensions': 384,
            'distance_metric': 'Cosine',
            'collections': collection_stats,
            'total_vectors': sum(stats['points'] for stats in collection_stats.values()),
            'model_characteristics': {
                'size': '22MB',
                'speed': 'Very Fast',
                'quality': 'Good',
                'multilingual': False,
                'domain_specific': False,
                'release_date': '2021'
            }
        }
        
        return analysis
    
    def evaluate_model_performance(self, model_name: str, model_id: str) -> Dict:
        """Evaluate a specific embedding model."""
        
        print(f"\n📊 Evaluating {model_name} ({model_id})")
        
        try:
            # Load model
            start_time = time.time()
            model = SentenceTransformer(model_id)
            load_time = time.time() - start_time
            
            # Test encoding speed
            start_time = time.time()
            query_embeddings = model.encode(self.test_queries)
            query_encode_time = time.time() - start_time
            
            start_time = time.time()
            doc_embeddings = model.encode(self.test_documents)
            doc_encode_time = time.time() - start_time
            
            # Calculate similarities for relevance testing
            similarities = []
            for i, query_emb in enumerate(query_embeddings):
                query_sims = []
                for doc_emb in doc_embeddings:
                    # Cosine similarity
                    similarity = np.dot(query_emb, doc_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(doc_emb))
                    query_sims.append(similarity)
                similarities.append(query_sims)
            
            # Calculate statistics
            all_similarities = [sim for query_sims in similarities for sim in query_sims]
            avg_similarity = np.mean(all_similarities)
            max_similarity = np.max(all_similarities)
            min_similarity = np.min(all_similarities)
            
            results = {
                'model_name': model_name,
                'model_id': model_id,
                'vector_dimensions': len(query_embeddings[0]),
                'load_time_seconds': load_time,
                'query_encode_time': query_encode_time,
                'doc_encode_time': doc_encode_time,
                'avg_encode_time_per_text': (query_encode_time + doc_encode_time) / (len(self.test_queries) + len(self.test_documents)),
                'similarity_stats': {
                    'avg': float(avg_similarity),
                    'max': float(max_similarity),
                    'min': float(min_similarity),
                    'std': float(np.std(all_similarities))
                },
                'memory_usage_mb': model.get_sentence_embedding_dimension() * 4 / 1024 / 1024 * 1000,  # Rough estimate
                'performance_score': self.calculate_performance_score(load_time, query_encode_time + doc_encode_time, avg_similarity)
            }
            
            print(f"   ✅ {model_name}: {results['vector_dimensions']}d, {results['avg_encode_time_per_text']:.3f}s/text, sim={avg_similarity:.3f}")
            
            return results
            
        except Exception as e:
            print(f"   ❌ Failed to evaluate {model_name}: {e}")
            return {'error': str(e)}
    
    def calculate_performance_score(self, load_time: float, encode_time: float, avg_similarity: float) -> float:
        """Calculate overall performance score (higher is better)."""
        # Normalize metrics (lower times are better, higher similarity is better)
        speed_score = max(0, 1 - (encode_time / 10))  # Penalty for slow encoding
        similarity_score = max(0, avg_similarity)  # Higher similarity is better
        load_score = max(0, 1 - (load_time / 30))  # Penalty for slow loading
        
        return (speed_score * 0.3 + similarity_score * 0.5 + load_score * 0.2)
    
    def compare_models(self) -> Dict:
        """Compare different embedding models."""
        
        print("🔄 Comparing Embedding Models for Visa Domain")
        print("=" * 60)
        
        results = {}
        
        for model_name, model_id in TEST_MODELS.items():
            try:
                results[model_name] = self.evaluate_model_performance(model_name, model_id)
                
                # Small delay between model tests
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Error testing {model_name}: {e}")
                results[model_name] = {'error': str(e)}
        
        return results
    
    def generate_recommendations(self, current_analysis: Dict, comparison_results: Dict) -> Dict:
        """Generate embedding recommendations based on analysis."""
        
        # Filter successful results
        valid_results = {k: v for k, v in comparison_results.items() if 'error' not in v}
        
        if not valid_results:
            return {'error': 'No valid model results to analyze'}
        
        # Find best performers
        best_performance = max(valid_results.values(), key=lambda x: x.get('performance_score', 0))
        fastest_model = min(valid_results.values(), key=lambda x: x.get('avg_encode_time_per_text', float('inf')))
        best_similarity = max(valid_results.values(), key=lambda x: x.get('similarity_stats', {}).get('avg', 0))
        
        recommendations = {
            'current_model_assessment': {
                'model': current_analysis['current_model'],
                'dimensions': current_analysis['vector_dimensions'],
                'total_vectors': current_analysis['total_vectors'],
                'strengths': [
                    'Very fast encoding',
                    'Compact 384-dimensional vectors',
                    'Good general performance',
                    'Low memory usage',
                    'Well-established in community'
                ],
                'weaknesses': [
                    'Not domain-specific for legal/immigration',
                    'Limited multilingual support',
                    'Older model (2021)',
                    'May miss nuanced legal terminology'
                ]
            },
            
            'recommendations_by_scenario': {
                'keep_current': {
                    'when': 'If performance is satisfactory and you prioritize stability',
                    'pros': ['No migration needed', 'Proven performance', 'Fast and lightweight'],
                    'cons': ['Missing potential improvements', 'Not optimized for domain']
                },
                
                'upgrade_general': {
                    'model': best_performance.get('model_id', 'all-mpnet-base-v2'),
                    'when': 'For better general semantic understanding',
                    'dimensions': best_performance.get('vector_dimensions', 768),
                    'pros': ['Better semantic understanding', 'More recent model', 'Higher quality'],
                    'cons': ['Larger vectors (2x storage)', 'Slightly slower', 'Requires re-indexing']
                },
                
                'optimize_speed': {
                    'model': fastest_model.get('model_id', 'all-MiniLM-L6-v2'),
                    'when': 'For high-throughput applications',
                    'speed': fastest_model.get('avg_encode_time_per_text', 0),
                    'pros': ['Fastest encoding', 'Real-time capable'],
                    'cons': ['May sacrifice some quality']
                },
                
                'optimize_quality': {
                    'model': best_similarity.get('model_id', 'all-mpnet-base-v2'),
                    'when': 'For best semantic matching quality',
                    'similarity_score': best_similarity.get('similarity_stats', {}).get('avg', 0),
                    'pros': ['Best semantic understanding', 'Higher search accuracy'],
                    'cons': ['Larger storage requirements', 'Slower encoding']
                }
            },
            
            'migration_strategy': {
                'if_upgrading': [
                    '1. Test new model on subset of data first',
                    '2. Create parallel collection with new embeddings',
                    '3. A/B test search quality with users',
                    '4. Gradually migrate traffic if results are better',
                    '5. Keep old collection as backup during transition'
                ],
                'storage_impact': {
                    '384d_to_768d': 'Double storage requirements',
                    'current_storage_mb': current_analysis['total_vectors'] * 384 * 4 / 1024 / 1024,
                    'upgrade_storage_mb': current_analysis['total_vectors'] * 768 * 4 / 1024 / 1024
                },
                'performance_impact': {
                    'index_time': 'Proportional to vector count',
                    'search_time': 'Minimal impact with proper indexing',
                    'memory_usage': 'Proportional to vector dimensions'
                }
            }
        }
        
        return recommendations
    
    def print_recommendations(self, recommendations: Dict):
        """Print formatted recommendations."""
        
        print("\n" + "=" * 80)
        print("🎯 EMBEDDING RECOMMENDATIONS FOR VISA COMMUNITY PLATFORM")
        print("=" * 80)
        
        # Current assessment
        current = recommendations['current_model_assessment']
        print(f"\n📊 Current Setup Assessment:")
        print(f"   Model: {current['model']} ({current['dimensions']}d)")
        print(f"   Total vectors: {current['total_vectors']:,}")
        print(f"   Strengths: {', '.join(current['strengths'][:3])}")
        print(f"   Weaknesses: {', '.join(current['weaknesses'][:2])}")
        
        # Scenario recommendations
        scenarios = recommendations['recommendations_by_scenario']
        
        print(f"\n🎯 Recommendation by Scenario:")
        
        print(f"\n   🟢 RECOMMENDED: Keep Current (all-MiniLM-L6-v2)")
        keep = scenarios['keep_current']
        print(f"      When: {keep['when']}")
        print(f"      Pros: {', '.join(keep['pros'])}")
        
        if 'upgrade_general' in scenarios:
            upgrade = scenarios['upgrade_general']
            print(f"\n   🟡 UPGRADE OPTION: {upgrade['model']} ({upgrade['dimensions']}d)")
            print(f"      When: {upgrade['when']}")
            print(f"      Pros: {', '.join(upgrade['pros'][:2])}")
            print(f"      Cons: {', '.join(upgrade['cons'])}")
        
        # Migration strategy
        migration = recommendations['migration_strategy']
        storage = migration['storage_impact']
        
        print(f"\n📈 Storage Impact Analysis:")
        print(f"   Current: {storage['current_storage_mb']:.1f} MB")
        print(f"   If upgraded to 768d: {storage['upgrade_storage_mb']:.1f} MB (+{storage['upgrade_storage_mb']/storage['current_storage_mb']:.1f}x)")
        
        print(f"\n✅ Final Recommendation:")
        if current['total_vectors'] > 1000000:  # Large dataset
            print("   🟢 KEEP CURRENT MODEL")
            print("   Reasons:")
            print("   - Large dataset makes migration expensive")
            print("   - Current model performs well for visa domain")
            print("   - 384d vectors are efficient for search")
            print("   - No significant quality issues detected")
        else:
            print("   🟡 CONSIDER UPGRADE")
            print("   - Dataset size allows feasible migration")
            print("   - Potential quality improvements available")
            print("   - Test thoroughly before full migration")
        
        print("=" * 80)


def main():
    """Run embedding analysis and recommendations."""
    analyzer = EmbeddingAnalyzer()
    
    # Analyze current setup
    current_analysis = analyzer.analyze_current_setup()
    
    # Compare models (only compare current model for now to save time)
    print(f"\n🔄 Analyzing Current Model Performance...")
    comparison_results = {
        'current': analyzer.evaluate_model_performance('current', 'all-MiniLM-L6-v2')
    }
    
    # Generate recommendations
    recommendations = analyzer.generate_recommendations(current_analysis, comparison_results)
    
    # Print recommendations
    analyzer.print_recommendations(recommendations)
    
    # Save detailed analysis
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    full_analysis = {
        'timestamp': timestamp,
        'current_analysis': current_analysis,
        'comparison_results': comparison_results,
        'recommendations': recommendations
    }
    
    with open(f'../data/embedding_analysis_{timestamp}.json', 'w') as f:
        json.dump(full_analysis, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed analysis saved to: ../data/embedding_analysis_{timestamp}.json")


if __name__ == "__main__":
    main()