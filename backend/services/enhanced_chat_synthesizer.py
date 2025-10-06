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
        
        # Lazy-load encoder (will be loaded on first use)
        self._encoder = None
        
        # Ollama settings
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model_name = os.getenv('LLM_MODEL', 'qwen')  # Fast 4B model
        
        logger.info(f"✅ Enhanced synthesizer ready!")
        logger.info(f"   Qdrant: {qdrant_host}:6333")
        logger.info(f"   Using: {self.model_name} at {self.ollama_host}")
        logger.info(f"   RedBus2US collection: {self.redbus_collection}")
    
    @property
    def encoder(self):
        """Lazy-load the sentence transformer model"""
        if self._encoder is None:
            logger.info("📥 Loading SentenceTransformer model (first use)...")
            self._encoder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            logger.info("✅ SentenceTransformer model loaded!")
        return self._encoder
    
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
                    limit=5  # Get top 5 most relevant articles
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
                    # Get first 500 chars of content for context
                    content = article.get('content', '')[:500]
                    context += f"Article {i}: {article.get('title', 'Untitled')}\n"
                    context += f"{content}...\n\n"
                    
                    sources.append({
                        "title": article.get('title', 'Untitled'),
                        "url": article.get('url', ''),
                        "date": article.get('published_date', ''),
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
        prompt = f"""You are an H1B visa expert. Answer the question using ONLY the information provided below. Do NOT make up or infer information not explicitly stated.

AUTHORITATIVE SOURCES:
{context}

USER QUESTION: {query}

INSTRUCTIONS:
1. Use ONLY the information from the articles above
2. If the articles contain the answer, provide specific details (fees, dates, requirements)
3. If the articles DO NOT contain the answer, say "The provided sources don't contain information about [topic]"
4. Be concise and direct
5. Do NOT add information from your general knowledge

ANSWER:"""
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Very low for factual, grounded responses
                            "num_predict": 400,  # Increased for more complete answers
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
