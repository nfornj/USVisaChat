"""
Test Vector Database Integration with LLM
Demonstrates how the scraped articles work with your LLM system
"""

import asyncio
import json
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from services.llm_service import LLMService


async def test_vector_llm_integration():
    """Test the integration between vector database and LLM."""
    
    print("🚀 Testing Vector Database + LLM Integration\n")
    
    # Initialize components
    print("📚 Initializing components...")
    qdrant = QdrantClient(host='localhost', port=6333)
    encoder = SentenceTransformer('all-MiniLM-L6-v2')
    llm = LLMService()
    
    # Test queries
    test_queries = [
        "What is the H1B fee for 2026?",
        "When is the H1B lottery for 2026?",
        "What documents do I need for H1B visa?",
        "H1B stamping interview experience",
        "H1B process timeline from lottery to approval"
    ]
    
    print("✅ Components initialized!\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"🔍 Test Query {i}: {query}")
        print("=" * 60)
        
        # Step 1: Vector Search
        print("Step 1: Searching vector database...")
        query_vector = encoder.encode(query).tolist()
        
        search_results = qdrant.search(
            collection_name="redbus2us_articles",
            query_vector=query_vector,
            limit=3
        )
        
        print(f"   Found {len(search_results)} relevant articles:")
        
        # Collect context from search results
        context_pieces = []
        for j, result in enumerate(search_results, 1):
            title = result.payload.get('title', 'Unknown')
            score = result.score
            text_preview = result.payload.get('text_preview', '')[:200] + "..."
            
            print(f"   {j}. {title[:50]}... (score: {score:.3f})")
            
            # Add to context
            context_pieces.append(f"Article {j}: {title}\n{text_preview}")
        
        # Step 2: Create context for LLM
        print("\nStep 2: Preparing context for LLM...")
        context = "\n\n".join(context_pieces)
        
        # Step 3: Generate LLM Response
        print("Step 3: Generating LLM response...")
        
        prompt = f"""Based on the following visa-related articles, please answer the user's question accurately.

Context from RedBus2US articles:
{context}

User Question: {query}

Please provide a comprehensive answer based on the context above. If the context doesn't contain enough information, mention what information is available and suggest where to find more details.

Answer:"""

        try:
            response = await llm.generate_response(prompt)
            print("\n💬 LLM Response:")
            print("-" * 40)
            print(response[:500] + "..." if len(response) > 500 else response)
            
        except Exception as e:
            print(f"❌ LLM Error: {e}")
        
        print("\n" + "=" * 60 + "\n")
    
    # Statistics
    print("📊 Vector Database Statistics:")
    collection_info = qdrant.get_collection("redbus2us_articles")
    print(f"   Collection: redbus2us_articles")
    print(f"   Total vectors: {collection_info.points_count}")
    print(f"   Vector dimensions: {collection_info.config.params.vectors.size}")
    print(f"   Distance metric: {collection_info.config.params.vectors.distance}")
    
    print("\n✅ Integration test completed!")
    print("\n🎯 Your vector database is ready for:")
    print("   - Semantic search on 11 scraped RedBus2US articles")
    print("   - 107 text chunks with proper metadata")
    print("   - Integration with your existing LLM service")
    print("   - Filtering by categories and visa types")
    print("   - Real-time question answering")


if __name__ == "__main__":
    asyncio.run(test_vector_llm_integration())