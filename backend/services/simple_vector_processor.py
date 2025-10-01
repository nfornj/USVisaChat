"""
Simple Vector Processor for Visa Conversations
Connects to your existing 767,253 vectors in Qdrant
"""

import asyncio
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import logging
import uuid
from dataclasses import dataclass

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class VectorConfig:
    """Configuration for vector processing"""
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = 384
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    collection_name: str = "visa_conversations"
    batch_size: int = 16

class SimpleVectorProcessor:
    """Simple vector processor for visa conversations"""
    
    def __init__(self, config: VectorConfig = None):
        self.config = config or VectorConfig()
        self.embedding_model = None
        self.qdrant_client = None
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize embedding model and vector database"""
        if self.is_initialized:
            return
            
        logger.info("🚀 Initializing Vector Processor...")
        
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers required. Run: uv add sentence-transformers")
        if not QDRANT_AVAILABLE:
            raise ImportError("qdrant-client required. Run: uv add qdrant-client")
        
        # Initialize embedding model
        logger.info(f"📥 Loading {self.config.embedding_model}")
        self.embedding_model = SentenceTransformer(self.config.embedding_model)
        
        # Initialize Qdrant client
        logger.info(f"🔗 Connecting to Qdrant at {self.config.qdrant_host}:{self.config.qdrant_port}")
        self.qdrant_client = QdrantClient(
            host=self.config.qdrant_host,
            port=self.config.qdrant_port
        )
        
        # Test connection
        collections = self.qdrant_client.get_collections()
        logger.info(f"✅ Connected to Qdrant ({len(collections.collections)} collections)")
        
        self.is_initialized = True
        logger.info("🎉 Vector Processor initialized!")
    
    async def semantic_search(self, query: str, filters: Dict = None, limit: int = 10) -> List[Dict]:
        """Perform semantic search on visa conversations"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            
            # Build filters if provided
            search_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    if value:
                        conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
                if conditions:
                    search_filter = Filter(must=conditions)
            
            # Search Qdrant
            results = self.qdrant_client.search(
                collection_name=self.config.collection_name,
                query_vector=query_embedding.tolist(),
                query_filter=search_filter,
                limit=limit,
                with_payload=True
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'id': result.id,
                    'score': float(result.score),
                    'text': result.payload.get('text', ''),
                    'metadata': result.payload
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector collection"""
        if not self.qdrant_client:
            return {'error': 'Qdrant not available'}
        
        try:
            collection_info = self.qdrant_client.get_collection(self.config.collection_name)
            return {
                'collection_name': self.config.collection_name,
                'total_vectors': collection_info.points_count,
                'status': collection_info.status,
                'vector_dimensions': self.config.embedding_dimensions,
                'embedding_model': self.config.embedding_model
            }
        except Exception as e:
            return {'error': str(e)}

# CLI interface
async def main():
    """Command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple Vector Processor")
    parser.add_argument("--search", type=str, help="Search query")
    parser.add_argument("--stats", action="store_true", help="Show collection statistics")
    parser.add_argument("--init-only", action="store_true", help="Just initialize")
    
    args = parser.parse_args()
    processor = SimpleVectorProcessor()
    
    try:
        if args.init_only:
            await processor.initialize()
            stats = await processor.get_collection_stats()
            print(f"📊 Collection Stats: {json.dumps(stats, indent=2)}")
        elif args.search:
            results = await processor.semantic_search(args.search, limit=5)
            print(f"🔍 Search results for: '{args.search}'")
            for i, result in enumerate(results, 1):
                print(f"{i}. Score: {result['score']:.3f}")
                print(f"   Text: {result['text'][:150]}...")
        elif args.stats:
            await processor.initialize()
            stats = await processor.get_collection_stats()
            print(f"📊 Statistics: {json.dumps(stats, indent=2)}")
        else:
            print("❓ Please specify --search, --stats, or --init-only")
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())