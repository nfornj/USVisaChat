"""
Generate vector embeddings from summarized RedBus2US articles.
Uses sentence-transformers for high-quality embeddings.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArticleVectorizer:
    """Generate and store vector embeddings for articles."""
    
    def __init__(self):
        self.summaries_dir = Path("data/redbus2us_summaries")
        self.vectors_dir = Path("data/redbus2us_vectors")
        self.vectors_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize sentence transformer
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dimensional embeddings
        
        # Initialize Qdrant client
        self.qdrant = QdrantClient(host="localhost", port=6333)
        self.collection_name = "redbus2us_articles"
        
        # Statistics
        self.stats = {
            'total_articles': 0,
            'total_chunks': 0,
            'by_category': {},
            'by_visa_type': {},
            'by_year': {}
        }
    
    def prepare_text_for_embedding(self, article: Dict) -> List[Dict]:
        """Prepare article text for embedding by creating strategic chunks."""
        chunks = []
        
        # Get article metadata
        title = article.get('title', '')
        url = article.get('url', '')
        published_date = article.get('published_date', '')
        category = article.get('category', 'Uncategorized')
        visa_type = article.get('visa_type', 'General')
        article_type = article.get('article_type', 'general')
        summary = article.get('summary', '')
        key_points = article.get('key_points', [])
        
        # Create chunks with different focuses
        
        # 1. Title + Summary chunk (most important)
        title_summary = f"Title: {title}\n\nSummary: {summary}"
        chunks.append({
            'text': title_summary,
            'type': 'title_summary',
            'metadata': {
                'title': title,
                'url': url,
                'published_date': published_date,
                'category': category,
                'visa_type': visa_type,
                'article_type': article_type,
                'chunk_type': 'title_summary'
            }
        })
        
        # 2. Key points chunk (if available)
        if key_points:
            key_points_text = "\n".join([f"- {point}" for point in key_points])
            chunks.append({
                'text': f"Key Points from {title}:\n{key_points_text}",
                'type': 'key_points',
                'metadata': {
                    'title': title,
                    'url': url,
                    'published_date': published_date,
                    'category': category,
                    'visa_type': visa_type,
                    'article_type': article_type,
                    'chunk_type': 'key_points'
                }
            })
        
        # 3. Timeline chunk (if available)
        if article.get('has_timeline', False):
            timeline_text = f"Timeline information from {title}:\n{summary}"
            chunks.append({
                'text': timeline_text,
                'type': 'timeline',
                'metadata': {
                    'title': title,
                    'url': url,
                    'published_date': published_date,
                    'category': category,
                    'visa_type': visa_type,
                    'article_type': article_type,
                    'chunk_type': 'timeline',
                    'has_timeline': True
                }
            })
        
        # 4. Fees chunk (if available)
        if article.get('has_fees', False):
            fees_text = f"Fee information from {title}:\n{summary}"
            chunks.append({
                'text': fees_text,
                'type': 'fees',
                'metadata': {
                    'title': title,
                    'url': url,
                    'published_date': published_date,
                    'category': category,
                    'visa_type': visa_type,
                    'article_type': article_type,
                    'chunk_type': 'fees',
                    'has_fees': True
                }
            })
        
        # 5. Documents chunk (if available)
        if article.get('has_documents', False):
            docs_text = f"Document requirements from {title}:\n{summary}"
            chunks.append({
                'text': docs_text,
                'type': 'documents',
                'metadata': {
                    'title': title,
                    'url': url,
                    'published_date': published_date,
                    'category': category,
                    'visa_type': visa_type,
                    'article_type': article_type,
                    'chunk_type': 'documents',
                    'has_documents': True
                }
            })
        
        return chunks
    
    def create_qdrant_collection(self):
        """Create or recreate the Qdrant collection."""
        # Check if collection exists
        collections = self.qdrant.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        # Delete if exists
        if exists:
            self.qdrant.delete_collection(self.collection_name)
        
        # Create new collection
        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=384,  # MiniLM-L6-v2 dimension
                distance=Distance.COSINE
            )
        )
        
        # Create payload indexes for efficient filtering
        self.qdrant.create_payload_index(
            collection_name=self.collection_name,
            field_name="category",
            field_schema="keyword"
        )
        self.qdrant.create_payload_index(
            collection_name=self.collection_name,
            field_name="visa_type",
            field_schema="keyword"
        )
        self.qdrant.create_payload_index(
            collection_name=self.collection_name,
            field_name="article_type",
            field_schema="keyword"
        )
        self.qdrant.create_payload_index(
            collection_name=self.collection_name,
            field_name="chunk_type",
            field_schema="keyword"
        )
        self.qdrant.create_payload_index(
            collection_name=self.collection_name,
            field_name="published_date",
            field_schema="keyword"
        )
    
    def process_summaries(self):
        """Process all summarized articles and create vector embeddings."""
        # Find the most recent summaries dataset
        input_files = list(self.summaries_dir.glob("summaries_complete_*.json"))
        if not input_files:
            logger.error("❌ No summarized articles found!")
            return
        
        latest_file = max(input_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"📂 Found latest summaries dataset: {latest_file}")
        
        # Load summarized articles
        with open(latest_file, 'r', encoding='utf-8') as f:
            summaries = json.load(f)
        
        # Create Qdrant collection
        logger.info("🔧 Creating Qdrant collection...")
        self.create_qdrant_collection()
        
        # Process articles by year
        all_chunks = []
        for year in summaries:
            self.stats['by_year'][year] = 0
            
            for month in summaries[year]:
                for category in summaries[year][month]:
                    if category not in self.stats['by_category']:
                        self.stats['by_category'][category] = 0
                    
                    for visa_type in summaries[year][month][category]:
                        if visa_type not in self.stats['by_visa_type']:
                            self.stats['by_visa_type'][visa_type] = 0
                        
                        articles = summaries[year][month][category][visa_type]
                        logger.info(f"📝 Processing {len(articles)} articles from {year}/{month} - {category} - {visa_type}")
                        
                        for article in articles:
                            self.stats['total_articles'] += 1
                            self.stats['by_year'][year] += 1
                            self.stats['by_category'][category] += 1
                            self.stats['by_visa_type'][visa_type] += 1
                            
                            # Create chunks for embedding
                            chunks = self.prepare_text_for_embedding(article)
                            all_chunks.extend(chunks)
                            self.stats['total_chunks'] += len(chunks)
                            
                            # Progress update
                            if self.stats['total_articles'] % 10 == 0:
                                logger.info(f"✅ Processed {self.stats['total_articles']} articles...")
        
        # Generate embeddings in batches
        batch_size = 32
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            
            # Generate embeddings
            texts = [chunk['text'] for chunk in batch]
            embeddings = self.model.encode(texts)
            
            # Upload to Qdrant
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=models.Batch(
                    ids=list(range(i, i + len(batch))),
                    vectors=embeddings.tolist(),
                    payloads=[chunk['metadata'] for chunk in batch]
                )
            )
        
        # Save vectors metadata
        self.save_vectors_metadata(all_chunks)
    
    def save_vectors_metadata(self, chunks: List[Dict]):
        """Save vectors metadata and statistics."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save metadata
        metadata = {
            'timestamp': timestamp,
            'model': 'all-MiniLM-L6-v2',
            'dimension': 384,
            'total_articles': self.stats['total_articles'],
            'total_chunks': self.stats['total_chunks'],
            'chunk_types': {
                'title_summary': len([c for c in chunks if c['type'] == 'title_summary']),
                'key_points': len([c for c in chunks if c['type'] == 'key_points']),
                'timeline': len([c for c in chunks if c['type'] == 'timeline']),
                'fees': len([c for c in chunks if c['type'] == 'fees']),
                'documents': len([c for c in chunks if c['type'] == 'documents'])
            },
            'by_category': self.stats['by_category'],
            'by_visa_type': self.stats['by_visa_type'],
            'by_year': self.stats['by_year']
        }
        
        metadata_file = self.vectors_dir / f"vectors_metadata_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Generate report
        report_file = self.vectors_dir / f"vectors_report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# RedBus2US Articles Vector Embeddings Report\n\n")
            
            f.write("## 📊 Overall Statistics\n\n")
            f.write(f"- Total articles processed: {self.stats['total_articles']}\n")
            f.write(f"- Total chunks created: {self.stats['total_chunks']}\n")
            f.write(f"- Average chunks per article: {self.stats['total_chunks'] / self.stats['total_articles']:.1f}\n\n")
            
            f.write("## 📋 Chunk Types\n\n")
            for chunk_type, count in metadata['chunk_types'].items():
                f.write(f"- {chunk_type}: {count} chunks\n")
            f.write("\n")
            
            f.write("## 📅 Articles by Year\n\n")
            for year in sorted(self.stats['by_year'].keys()):
                f.write(f"- {year}: {self.stats['by_year'][year]} articles\n")
            f.write("\n")
            
            f.write("## 📋 Articles by Category\n\n")
            for category in sorted(self.stats['by_category'].keys()):
                f.write(f"- {category}: {self.stats['by_category'][category]} articles\n")
            f.write("\n")
            
            f.write("## 🎯 Articles by Visa Type\n\n")
            for visa_type in sorted(self.stats['by_visa_type'].keys()):
                f.write(f"- {visa_type}: {self.stats['by_visa_type'][visa_type]} articles\n")
            f.write("\n")
            
            f.write("## 🔍 Vector Details\n\n")
            f.write("- Model: all-MiniLM-L6-v2\n")
            f.write("- Dimension: 384\n")
            f.write("- Distance metric: Cosine similarity\n")
            f.write("- Collection name: redbus2us_articles\n")
            f.write("- Payload indexes: category, visa_type, article_type, chunk_type, published_date\n")
        
        logger.info("\n" + "="*80)
        logger.info("✅ Vector generation completed successfully!")
        logger.info(f"📊 Total articles: {self.stats['total_articles']}")
        logger.info(f"📊 Total chunks: {self.stats['total_chunks']}")
        logger.info(f"📁 Data saved to: {self.vectors_dir}")
        logger.info(f"📄 Report generated: {report_file}")
        logger.info("="*80)

def main():
    """Run the article vectorizer."""
    vectorizer = ArticleVectorizer()
    vectorizer.process_summaries()

if __name__ == "__main__":
    main()


