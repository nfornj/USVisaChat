"""
Enhanced Chat Synthesizer - Combines community chat and RedBus2US knowledge.
Uses Qdrant for semantic search and LLM for response generation.
"""

import logging
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from .llm_service import llm_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedChatSynthesizer:
    """Enhanced chat synthesizer with RedBus2US knowledge."""
    
    def __init__(self, qdrant_host: str = "localhost"):
        """Initialize the chat synthesizer."""
        self.qdrant = QdrantClient(host=qdrant_host, port=6333)
        self.llm_service = llm_service
        
        # Collection names
        self.chat_collection = "visa_conversations"
        self.redbus_collection = "redbus2us_articles"
        
        # Load RedBus2US metadata
        self.redbus_metadata = self.load_redbus_metadata()
        
        logger.info(f"✅ Enhanced synthesizer ready!")
        logger.info(f"   Qdrant: {qdrant_host}:6333")
        logger.info(f"   LLM Provider: {self.llm_service.get_provider_info()['provider']}")
        logger.info(f"   RedBus2US collection: {self.redbus_collection}")
    
    def load_redbus_metadata(self) -> Dict:
        """Load RedBus2US metadata for statistics."""
        try:
            vectors_dir = Path("data/redbus2us_vectors")
            metadata_files = list(vectors_dir.glob("vectors_metadata_*.json"))
            if not metadata_files:
                return {}
            
            latest_file = max(metadata_files, key=lambda x: x.stat().st_mtime)
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Could not load RedBus2US metadata: {e}")
            return {}
    
    def get_visa_type_filter(self, query: str) -> Optional[str]:
        """Detect visa type from query for filtering."""
        query_lower = query.lower()
        
        visa_types = {
            'H1B': ['h1b', 'h-1b', 'h1-b', 'h1 b'],
            'F1': ['f1', 'f-1', 'f1 visa', 'student visa'],
            'B1/B2': ['b1', 'b2', 'b1/b2', 'tourist', 'business visa'],
            'H4': ['h4', 'h-4', 'dependent'],
            'L1': ['l1', 'l-1', 'intracompany'],
            'Green Card': ['green card', 'permanent resident', 'gc']
        }
        
        for visa_type, keywords in visa_types.items():
            if any(keyword in query_lower for keyword in keywords):
                return visa_type
        
        return None
    
    def get_topic_filter(self, query: str) -> Optional[str]:
        """Detect topic from query for filtering."""
        query_lower = query.lower()
        
        topics = {
            'dropbox_process': ['dropbox', 'stamping', 'interview waiver'],
            'documents': ['document', 'requirement', 'checklist', 'papers'],
            'process_timeline': ['timeline', 'process', 'step', 'procedure', 'how long'],
            'fees': ['fee', 'cost', 'price', 'payment', 'how much'],
            'interview': ['interview', 'question', 'preparation', 'consul'],
            'policy_updates': ['policy', 'rule', 'change', 'update', 'new'],
            'visa_denial': ['denial', 'reject', 'refuse', '221g', 'rejected'],
            'administrative_processing': ['administrative', 'ap', 'processing'],
            'travel_restrictions': ['travel', 'restriction', 'ban', 'covid'],
            'embassy_updates': ['embassy', 'consulate', 'closure']
        }
        
        for topic, keywords in topics.items():
            if any(keyword in query_lower for keyword in keywords):
                return topic
        
        return None
    
    async def search_redbus_articles(
        self,
        query: str,
        visa_type: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Search RedBus2US articles with filters."""
        try:
            # Build filter conditions
            filter_conditions = []
            
            if visa_type:
                filter_conditions.append(
                    FieldCondition(
                        key="visa_type",
                        match=MatchValue(value=visa_type)
                    )
                )
            
            if topic:
                filter_conditions.append(
                    FieldCondition(
                        key="article_type",
                        match=MatchValue(value=topic)
                    )
                )
            
            # Search with filters
            results = self.qdrant.search(
                collection_name=self.redbus_collection,
                query_vector=self.llm_service.model.encode(query).tolist(),
                query_filter=Filter(must=filter_conditions) if filter_conditions else None,
                limit=limit
            )
            
            # Format results
            articles = []
            for hit in results:
                article = {
                    'title': hit.payload.get('title', 'No title'),
                    'url': hit.payload.get('url', ''),
                    'published_date': hit.payload.get('published_date', ''),
                    'category': hit.payload.get('category', 'Uncategorized'),
                    'visa_type': hit.payload.get('visa_type', 'General'),
                    'article_type': hit.payload.get('article_type', 'general'),
                    'chunk_type': hit.payload.get('chunk_type', 'unknown'),
                    'score': hit.score
                }
                articles.append(article)
            
            return articles
        
        except Exception as e:
            logger.error(f"❌ Error searching RedBus2US articles: {e}")
            return []
    
    async def search_community_chat(
        self,
        query: str,
        visa_type: Optional[str] = None,
        limit: int = 3
    ) -> List[Dict]:
        """Search community chat messages with filters."""
        try:
            # Build filter conditions
            filter_conditions = []
            
            if visa_type:
                filter_conditions.append(
                    FieldCondition(
                        key="visa_type",
                        match=MatchValue(value=visa_type)
                    )
                )
            
            # Search with filters
            results = self.qdrant.search(
                collection_name=self.chat_collection,
                query_vector=self.llm_service.model.encode(query).tolist(),
                query_filter=Filter(must=filter_conditions) if filter_conditions else None,
                limit=limit
            )
            
            # Format results
            messages = []
            for hit in results:
                message = {
                    'text': hit.payload.get('text', ''),
                    'visa_type': hit.payload.get('visa_type', 'Unknown'),
                    'category': hit.payload.get('category', 'General'),
                    'score': hit.score
                }
                messages.append(message)
            
            return messages
        
        except Exception as e:
            logger.error(f"❌ Error searching community chat: {e}")
            return []
    
    async def generate_response(self, query: str) -> Tuple[str, List[Dict]]:
        """Generate response using both RedBus2US and community knowledge."""
        try:
            # Detect filters from query
            visa_type = self.get_visa_type_filter(query)
            topic = self.get_topic_filter(query)
            
            # Search both sources
            redbus_articles = await self.search_redbus_articles(
                query=query,
                visa_type=visa_type,
                topic=topic,
                limit=5
            )
            
            chat_messages = await self.search_community_chat(
                query=query,
                visa_type=visa_type,
                limit=3
            )
            
            # Prepare context for LLM
            context = []
            
            # Add RedBus2US articles
            if redbus_articles:
                context.append("\nAuthoritative Information from RedBus2US:")
                for article in redbus_articles:
                    context.append(f"\nTitle: {article['title']}")
                    context.append(f"Category: {article['category']}")
                    context.append(f"Type: {article['article_type']}")
                    context.append(f"URL: {article['url']}")
            
            # Add community experiences
            if chat_messages:
                context.append("\nCommunity Experiences:")
                for msg in chat_messages:
                    context.append(f"\nVisa Type: {msg['visa_type']}")
                    context.append(f"Category: {msg['category']}")
                    context.append(f"Experience: {msg['text']}")
            
            # Generate response
            system_prompt = """You are a visa expert assistant. Your goal is to provide accurate, helpful information about US visas.

Rules:
1. Use authoritative sources (RedBus2US) as primary references
2. Support with real community experiences when relevant
3. Be clear about timelines, fees, and requirements
4. Highlight any recent changes or updates
5. Stay factual and avoid speculation
6. If information is unclear or missing, say so
7. Format response for readability (bullet points, sections)
8. Include source attribution when appropriate

Remember: Your advice impacts people's visa journeys. Be accurate and helpful."""

            prompt = f"""Question: {query}

Available Information:
{''.join(context)}

Please provide a comprehensive answer using the available information. Focus on accuracy and clarity."""

            answer = await self.llm_service.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,  # Very low for factual responses
                max_tokens=800    # Allow longer responses
            )
            
            # Prepare sources for frontend
            sources = []
            
            # Add RedBus2US articles as sources
            for article in redbus_articles:
                sources.append({
                    'type': 'redbus2us',
                    'title': article['title'],
                    'url': article['url'],
                    'published_date': article['published_date'],
                    'category': article['category'],
                    'visa_type': article['visa_type'],
                    'article_type': article['article_type'],
                    'relevance': round(article['score'] * 100, 1)
                })
            
            # Add community messages as sources
            for msg in chat_messages:
                sources.append({
                    'type': 'community',
                    'text': msg['text'],
                    'visa_type': msg['visa_type'],
                    'category': msg['category'],
                    'relevance': round(msg['score'] * 100, 1)
                })
            
            return answer.strip(), sources
            
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            return "I apologize, but I encountered an error while generating the response. Please try again.", []