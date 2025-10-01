"""
Load RedBus2US H1B articles into Qdrant Vector Database
Creates a separate collection for authoritative content
"""

import json
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_redbus_articles_to_qdrant():
    """Load RedBus2US articles into Qdrant"""
    
    # Initialize
    logger.info("🚀 Loading RedBus2US articles into Qdrant...")
    
    # Load articles
    with open('data/redbus2us_h1b_articles.json', 'r') as f:
        articles = json.load(f)
    
    logger.info(f"📚 Loaded {len(articles)} articles from JSON")
    
    # Initialize Qdrant
    client = QdrantClient(host='localhost', port=6333)
    collection_name = "redbus2us_articles"
    
    # Initialize encoder
    logger.info("🔍 Loading SentenceTransformer model...")
    encoder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    # Check if collection exists, recreate it
    collections = client.get_collections().collections
    if any(col.name == collection_name for col in collections):
        logger.info(f"🗑️  Deleting existing collection: {collection_name}")
        client.delete_collection(collection_name)
    
    # Create collection
    logger.info(f"✨ Creating collection: {collection_name}")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    
    # Prepare points
    points = []
    for article in articles:
        # Create searchable text
        text = f"{article['title']}\n\n{article['excerpt']}"
        
        # Generate embedding
        vector = encoder.encode(text).tolist()
        
        # Create point
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                'title': article['title'],
                'url': article['url'],
                'excerpt': article['excerpt'],
                'published_date': article['published_date'],
                'categories': article['categories'],
                'source': 'RedBus2US',
                'text': text,  # For retrieval
                'scraped_at': article['scraped_at']
            }
        )
        points.append(point)
    
    # Upload to Qdrant
    logger.info(f"⬆️  Uploading {len(points)} articles to Qdrant...")
    client.upsert(
        collection_name=collection_name,
        points=points
    )
    
    # Verify
    collection_info = client.get_collection(collection_name)
    logger.info(f"✅ Collection created successfully!")
    logger.info(f"   Collection: {collection_name}")
    logger.info(f"   Points: {collection_info.points_count}")
    logger.info(f"   Vector size: {collection_info.config.params.vectors.size}")
    
    # Test search
    logger.info("\n🔍 Testing semantic search...")
    test_query = "What is the H1B fee for 2026?"
    test_vector = encoder.encode(test_query).tolist()
    
    results = client.search(
        collection_name=collection_name,
        query_vector=test_vector,
        limit=3
    )
    
    logger.info(f"   Query: '{test_query}'")
    logger.info(f"   Top results:")
    for i, result in enumerate(results, 1):
        logger.info(f"   {i}. {result.payload['title']} (score: {result.score:.3f})")
    
    print("\n" + "="*70)
    print("✅ RedBus2US articles loaded into Qdrant successfully!")
    print("="*70)
    print(f"Collection: {collection_name}")
    print(f"Articles: {len(articles)}")
    print(f"Ready for semantic search!")
    print("="*70 + "\n")


if __name__ == "__main__":
    import os
    os.chdir('/Users/neekrish/Documents/GitHub/MyAI/Visa')
    load_redbus_articles_to_qdrant()
