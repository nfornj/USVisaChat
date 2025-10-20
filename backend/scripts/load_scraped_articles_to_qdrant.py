"""
Load scraped RedBus2US articles into Qdrant Vector Database
Works with the new scraped article format from simplified_redbus_scraper.py
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ScrapedArticleVectorizer:
    """Load scraped articles into Qdrant vector database."""
    
    def __init__(self):
        # Paths
        self.articles_dir = Path("../data/redbus2us_raw/articles")
        
        # Initialize sentence transformer (same model as existing system)
        logger.info("🔍 Loading SentenceTransformer model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dimensional embeddings
        
        # Initialize Qdrant client
        qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
        qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
        self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = "redbus2us_articles"
        
        # Statistics
        self.stats = {
            'articles_processed': 0,
            'chunks_created': 0,
            'by_category': {},
            'by_visa_type': {}
        }
    
    def load_scraped_articles(self) -> List[Dict]:
        """Load all scraped articles from JSON files."""
        articles = []
        
        if not self.articles_dir.exists():
            logger.error(f"❌ Articles directory not found: {self.articles_dir}")
            return articles
        
        # Find all JSON files
        json_files = list(self.articles_dir.glob("*.json"))
        logger.info(f"📂 Found {len(json_files)} article files")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'article' in data:
                        articles.append(data['article'])
            except Exception as e:
                logger.error(f"❌ Error loading {json_file}: {e}")
        
        logger.info(f"📚 Successfully loaded {len(articles)} articles")
        return articles
    
    def create_text_chunks(self, article: Dict) -> List[Dict]:
        """Create text chunks from article for better search granularity."""
        chunks = []
        
        title = article.get('title', '')
        content = article.get('content', '')
        url = article.get('url', '')
        published_date = article.get('published_date', '')
        categories = article.get('categories', [])
        visa_types = article.get('visa_types', [])
        
        # Chunk 1: Title + First part of content (overview)
        content_preview = content[:1000] if content else ''
        overview_text = f"Title: {title}\n\nOverview: {content_preview}"
        
        chunks.append({
            'text': overview_text,
            'chunk_type': 'title_overview',
            'metadata': {
                'title': title,
                'url': url,
                'published_date': published_date,
                'categories': categories,
                'visa_types': visa_types,
                'chunk_type': 'title_overview',
                'source': 'RedBus2US_Scraped'
            }
        })
        
        # Chunk 2: Full content in manageable pieces
        if len(content) > 1000:
            # Split content into chunks of ~1500 characters with overlap
            chunk_size = 1500
            overlap = 200
            
            for i in range(0, len(content), chunk_size - overlap):
                chunk_content = content[i:i + chunk_size]
                if len(chunk_content.strip()) > 100:  # Only add substantial chunks
                    chunks.append({
                        'text': f"Content from '{title}':\n\n{chunk_content}",
                        'chunk_type': 'content',
                        'metadata': {
                            'title': title,
                            'url': url,
                            'published_date': published_date,
                            'categories': categories,
                            'visa_types': visa_types,
                            'chunk_type': 'content',
                            'chunk_index': len(chunks),
                            'source': 'RedBus2US_Scraped'
                        }
                    })
        
        return chunks
    
    def create_qdrant_collection(self):
        """Create or recreate the Qdrant collection."""
        # Check if collection exists
        collections = self.qdrant.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if exists:
            logger.info(f"🗑️ Deleting existing collection: {self.collection_name}")
            self.qdrant.delete_collection(self.collection_name)
        
        # Create new collection
        logger.info(f"✨ Creating collection: {self.collection_name}")
        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=384,  # MiniLM-L6-v2 dimension
                distance=Distance.COSINE
            )
        )
        
        # Create payload indexes for efficient filtering
        logger.info("🔧 Creating payload indexes...")
        
        try:
            self.qdrant.create_payload_index(
                collection_name=self.collection_name,
                field_name="categories",
                field_schema="keyword"
            )
            self.qdrant.create_payload_index(
                collection_name=self.collection_name,
                field_name="visa_types", 
                field_schema="keyword"
            )
            self.qdrant.create_payload_index(
                collection_name=self.collection_name,
                field_name="chunk_type",
                field_schema="keyword"
            )
            self.qdrant.create_payload_index(
                collection_name=self.collection_name,
                field_name="source",
                field_schema="keyword"
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not create some indexes: {e}")
    
    def process_articles(self):
        """Process articles and upload to Qdrant."""
        # Load articles
        articles = self.load_scraped_articles()
        if not articles:
            logger.error("❌ No articles to process!")
            return
        
        # Create collection
        self.create_qdrant_collection()
        
        # Process articles
        all_points = []
        point_id = 0
        
        for article in articles:
            try:
                # Create chunks
                chunks = self.create_text_chunks(article)
                self.stats['chunks_created'] += len(chunks)
                
                # Update stats
                for category in article.get('categories', []):
                    self.stats['by_category'][category] = self.stats['by_category'].get(category, 0) + 1
                
                for visa_type in article.get('visa_types', []):
                    self.stats['by_visa_type'][visa_type] = self.stats['by_visa_type'].get(visa_type, 0) + 1
                
                # Generate embeddings and create points
                for chunk in chunks:
                    # Generate embedding
                    vector = self.model.encode(chunk['text']).tolist()
                    
                    # Create point
                    point = PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            **chunk['metadata'],
                            'text_preview': chunk['text'][:500],  # Store preview for display
                            'full_text': chunk['text']  # Store full text for context
                        }
                    )
                    all_points.append(point)
                    point_id += 1
                
                self.stats['articles_processed'] += 1
                logger.info(f"✅ Processed article {self.stats['articles_processed']}/{len(articles)}: {article.get('title', 'Unknown')[:50]}...")
                
            except Exception as e:
                logger.error(f"❌ Error processing article: {e}")
        
        # Upload to Qdrant in batches
        batch_size = 50
        logger.info(f"⬆️ Uploading {len(all_points)} vectors to Qdrant in batches...")
        
        for i in range(0, len(all_points), batch_size):
            batch = all_points[i:i + batch_size]
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=batch
            )
            logger.info(f"📤 Uploaded batch {i//batch_size + 1}/{(len(all_points) + batch_size - 1)//batch_size}")
        
        # Verify collection
        collection_info = self.qdrant.get_collection(self.collection_name)
        logger.info(f"✅ Collection created successfully!")
        logger.info(f"   Collection: {self.collection_name}")
        logger.info(f"   Points: {collection_info.points_count}")
        logger.info(f"   Vector size: {collection_info.config.params.vectors.size}")
    
    def test_search(self):
        """Test the vector search with sample queries."""
        test_queries = [
            "What is the H1B fee for 2026?",
            "H1B lottery process timeline",
            "Documents required for H1B petition",
            "H1B visa stamping experiences"
        ]
        
        logger.info("\n🔍 Testing semantic search...")
        
        for query in test_queries:
            # Generate query vector
            query_vector = self.model.encode(query).tolist()
            
            # Search
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=3
            )
            
            logger.info(f"\n   Query: '{query}'")
            logger.info(f"   Top results:")
            for i, result in enumerate(results, 1):
                title = result.payload.get('title', 'Unknown')
                score = result.score
                chunk_type = result.payload.get('chunk_type', 'unknown')
                logger.info(f"   {i}. [{chunk_type}] {title[:60]}... (score: {score:.3f})")
    
    def print_summary(self):
        """Print processing summary."""
        print("\n" + "="*80)
        print("✅ RedBus2US articles loaded into Qdrant successfully!")
        print("="*80)
        print(f"📊 Articles processed: {self.stats['articles_processed']}")
        print(f"📊 Chunks created: {self.stats['chunks_created']}")
        print(f"📊 Avg chunks per article: {self.stats['chunks_created']/max(self.stats['articles_processed'], 1):.1f}")
        print(f"🏷️  Collection: {self.collection_name}")
        
        if self.stats['by_category']:
            print(f"\n📋 Categories:")
            for category, count in self.stats['by_category'].items():
                print(f"   - {category}: {count}")
        
        if self.stats['by_visa_type']:
            print(f"\n🎯 Visa Types:")
            for visa_type, count in self.stats['by_visa_type'].items():
                print(f"   - {visa_type}: {count}")
        
        print("\n🚀 Ready for semantic search queries!")
        print("="*80 + "\n")


def main():
    """Main function."""
    vectorizer = ScrapedArticleVectorizer()
    
    # Process articles
    vectorizer.process_articles()
    
    # Test search
    vectorizer.test_search()
    
    # Print summary
    vectorizer.print_summary()


if __name__ == "__main__":
    main()