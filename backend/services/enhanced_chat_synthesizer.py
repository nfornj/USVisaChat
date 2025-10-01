"""
Enhanced Chat Synthesizer with RedBus2US Knowledge
Uses Qdrant to search authoritative H1B content and generates intelligent answers
"""

import os
import logging
from typing import Dict, List
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import httpx
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedChatSynthesizer:
    """
    Enhanced synthesizer that combines:
    1. RedBus2US authoritative articles (from Qdrant)
    2. Local LLM for answer generation
    """
    
    def __init__(self):
        logger.info("🤖 Initializing Enhanced Chat Synthesizer...")
        
        # Qdrant connection (use env variable for Docker compatibility)
        qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
        self.qdrant = QdrantClient(host=qdrant_host, port=6333)
        self.redbus_collection = "redbus2us_articles"
        
        # Sentence encoder for semantic search
        self.encoder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Ollama settings
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model_name = os.getenv('LLM_MODEL', 'qwen')  # Fast 4B model
        
        logger.info(f"✅ Enhanced synthesizer ready!")
        logger.info(f"   Qdrant: {qdrant_host}:6333")
        logger.info(f"   Using: {self.model_name} at {self.ollama_host}")
        logger.info(f"   RedBus2US collection: {self.redbus_collection}")
    
    async def synthesize_answer(self, query: str, use_redbus: bool = True) -> Dict:
        """
        Generate an intelligent answer for a query
        
        Args:
            query: User's question
            use_redbus: Whether to use RedBus2US knowledge (default: True)
        
        Returns:
            Dict with answer, sources, and metadata
        """
        logger.info(f"🔍 Processing query: {query}")
        
        try:
            if use_redbus:
                # Search RedBus2US knowledge base
                query_vector = self.encoder.encode(query).tolist()
                
                search_results = self.qdrant.search(
                    collection_name=self.redbus_collection,
                    query_vector=query_vector,
                    limit=3
                )
                
                if not search_results:
                    return {
                        "answer": "I don't have specific information about that in the RedBus2US H1B knowledge base.",
                        "sources": [],
                        "confidence": 0,
                        "type": "no_results"
                    }
                
                # Build context from articles
                context = "H1B Visa Information from RedBus2US:\n\n"
                sources = []
                
                for i, result in enumerate(search_results, 1):
                    article = result.payload
                    context += f"{i}. {article['title']}\n"
                    context += f"   {article['excerpt'][:250]}...\n\n"
                    
                    sources.append({
                        "title": article['title'],
                        "url": article['url'],
                        "date": article['published_date'],
                        "relevance_score": result.score
                    })
                
                # Generate answer using LLM
                answer = await self._generate_llm_answer(query, context)
                
                return {
                    "answer": answer,
                    "sources": sources,
                    "confidence": int(search_results[0].score * 100),
                    "type": "redbus_knowledge",
                    "articles_found": len(search_results)
                }
            
            else:
                # Fallback: simple response
                return {
                    "answer": "Please enable RedBus2US knowledge to get authoritative answers.",
                    "sources": [],
                    "confidence": 0,
                    "type": "fallback"
                }
        
        except Exception as e:
            logger.error(f"Error synthesizing answer: {e}")
            return {
                "answer": f"Sorry, I encountered an error: {str(e)}",
                "sources": [],
                "confidence": 0,
                "type": "error"
            }
    
    async def _generate_llm_answer(self, query: str, context: str) -> str:
        """Generate answer using local LLM"""
        prompt = f"""Answer this H1B visa question using the information provided.

{context}

Question: {query}

Provide a clear, direct answer with specific details (fees, dates, timelines). Be concise and helpful.

Answer:"""
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_predict": 300,
                        }
                    }
                )
                
                if response.status_code == 200:
                    answer = response.json()['response']
                    logger.info(f"✅ Generated answer ({len(answer)} chars)")
                    return answer.strip()
                else:
                    return "I encountered an error generating the answer. Please try again."
        
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return f"Error generating answer: {str(e)}"


# For backward compatibility with existing code
class ChatSynthesizer(EnhancedChatSynthesizer):
    """Alias for backward compatibility"""
    pass
