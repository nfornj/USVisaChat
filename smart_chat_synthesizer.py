"""
Smart Chat Synthesizer - Give real answers using knowledge base
Combines extracted conversation knowledge with RedBus2US authoritative content
Uses LOCAL LLM (Ollama) - No API keys needed!
"""

import logging
import json
import os
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmartChatSynthesizer:
    """Smart chat synthesizer using knowledge base and LOCAL LLM"""
    
    def __init__(self):
        # Use Ollama (local LLM) instead of OpenAI
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model_name = os.getenv('LLM_MODEL', 'llama3.2')
        self.encoder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        logger.info(f"🤖 Using LOCAL LLM: {self.model_name}")
        
        # Load knowledge bases
        self.conversation_knowledge = self.load_knowledge('data/knowledge_base.json')
        self.redbus_knowledge = self.load_knowledge('data/redbus2us_articles.json')
        
        logger.info(f"📚 Loaded {len(self.conversation_knowledge)} conversation Q&As")
        logger.info(f"📚 Loaded {len(self.redbus_knowledge)} RedBus2US articles")
    
    def load_knowledge(self, filepath: str) -> List[Dict]:
        """Load knowledge base from file"""
        if not os.path.exists(filepath):
            logger.warning(f"Knowledge file not found: {filepath}")
            return []
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def search_conversation_knowledge(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search conversation knowledge base"""
        if not self.conversation_knowledge:
            return []
        
        # Encode query
        query_embedding = self.encoder.encode(query)
        
        # Encode all questions
        scored_knowledge = []
        for entry in self.conversation_knowledge:
            question = entry.get('question', '')
            if not question:
                continue
            
            # Calculate similarity
            q_embedding = self.encoder.encode(question)
            similarity = np.dot(query_embedding, q_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(q_embedding)
            )
            
            scored_knowledge.append({
                **entry,
                'similarity': similarity
            })
        
        # Sort by similarity
        scored_knowledge.sort(key=lambda x: x['similarity'], reverse=True)
        
        return scored_knowledge[:top_k]
    
    def search_redbus_articles(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search RedBus2US articles"""
        if not self.redbus_knowledge:
            return []
        
        query_lower = query.lower()
        
        # Simple keyword-based search (can be improved with embeddings)
        scored_articles = []
        for article in self.redbus_knowledge:
            title = article.get('title', '').lower()
            content = article.get('content', '').lower()
            
            # Calculate relevance score
            score = 0
            if any(word in title for word in query_lower.split()):
                score += 3
            if any(word in content for word in query_lower.split()):
                score += 1
            
            if score > 0:
                scored_articles.append({
                    **article,
                    'relevance_score': score
                })
        
        # Sort by relevance
        scored_articles.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return scored_articles[:top_k]
    
    async def synthesize_answer(self, query: str) -> Dict:
        """
        Synthesize answer from knowledge base
        Returns: {answer, sources, confidence, has_knowledge}
        """
        logger.info(f"🔍 Synthesizing answer for: {query}")
        
        # Search knowledge bases
        conversation_qa = self.search_conversation_knowledge(query, top_k=5)
        redbus_articles = self.search_redbus_articles(query, top_k=3)
        
        has_knowledge = len(conversation_qa) > 0 or len(redbus_articles) > 0
        
        if not has_knowledge:
            return {
                'answer': "I don't have specific knowledge about this yet. Would you like me to search the community conversations?",
                'sources': [],
                'confidence': 0,
                'has_knowledge': False
            }
        
        # Build context for GPT
        context = self._build_context(conversation_qa, redbus_articles)
        
        # Use LOCAL LLM to synthesize answer
        try:
            system_prompt = "You are an expert visa consultant providing accurate, helpful answers based on community knowledge and official sources."
            
            prompt = f"""You are a helpful visa assistant. Answer the user's question using ONLY the provided knowledge.

User Question: {query}

Available Knowledge:
{context}

Instructions:
1. Provide a clear, direct answer to the question
2. Use bullet points for lists (documents, steps, etc.)
3. Include timelines, fees, and specific details from the knowledge
4. Be concise but complete
5. If knowledge mentions recent policy changes, highlight them
6. DO NOT make up information - only use what's provided
7. If the knowledge doesn't fully answer the question, say so

Format your answer in a helpful, structured way."""

            # Call local LLM
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": f"{system_prompt}\n\n{prompt}",
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 800,
                        }
                    }
                )
                
                if response.status_code == 200:
                    answer = response.json()['response']
                else:
                    raise Exception(f"Ollama error: {response.status_code}")
            
            # Build sources
            sources = self._build_sources(conversation_qa, redbus_articles)
            
            return {
                'answer': answer,
                'sources': sources,
                'confidence': self._calculate_confidence(conversation_qa, redbus_articles),
                'has_knowledge': True
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing answer: {e}")
            return {
                'answer': "Sorry, I encountered an error generating the answer.",
                'sources': [],
                'confidence': 0,
                'has_knowledge': False
            }
    
    def _build_context(self, conversation_qa: List[Dict], articles: List[Dict]) -> str:
        """Build context for GPT from knowledge bases"""
        context_parts = []
        
        # Add conversation Q&As
        if conversation_qa:
            context_parts.append("📱 Community Knowledge:")
            for i, qa in enumerate(conversation_qa[:3], 1):
                context_parts.append(f"\n{i}. Q: {qa.get('question')}")
                context_parts.append(f"   A: {qa.get('answer')}")
                if qa.get('key_facts'):
                    context_parts.append(f"   Key Facts: {', '.join(qa['key_facts'][:3])}")
        
        # Add RedBus2US articles
        if articles:
            context_parts.append("\n\n📰 Official Sources (RedBus2US):")
            for i, article in enumerate(articles[:2], 1):
                context_parts.append(f"\n{i}. {article.get('title')}")
                content = article.get('content', '')[:500]  # First 500 chars
                context_parts.append(f"   {content}")
                if article.get('key_points'):
                    context_parts.append(f"   Key Points: {'; '.join(article['key_points'][:3])}")
        
        return '\n'.join(context_parts)
    
    def _build_sources(self, conversation_qa: List[Dict], articles: List[Dict]) -> List[Dict]:
        """Build source list for attribution"""
        sources = []
        
        # Conversation sources
        for qa in conversation_qa[:3]:
            sources.append({
                'type': 'community',
                'title': qa.get('question', '')[:60] + '...',
                'confidence': qa.get('confidence', 0),
                'category': qa.get('category', 'general')
            })
        
        # RedBus2US sources
        for article in articles[:2]:
            sources.append({
                'type': 'official',
                'title': article.get('title', ''),
                'url': article.get('url', ''),
                'published': article.get('published_date', '')
            })
        
        return sources
    
    def _calculate_confidence(self, conversation_qa: List[Dict], articles: List[Dict]) -> int:
        """Calculate overall confidence in the answer"""
        if not conversation_qa and not articles:
            return 0
        
        # Weight: Official articles higher, conversation QA lower
        confidence = 0
        
        if articles:
            confidence += 50  # Base confidence if we have official sources
            if any('2025' in a.get('published_date', '') for a in articles):
                confidence += 20  # Recent articles
        
        if conversation_qa:
            avg_conv_confidence = sum(qa.get('confidence', 0) for qa in conversation_qa) / len(conversation_qa)
            confidence += min(30, avg_conv_confidence * 0.3)  # Up to 30 points from conversations
        
        return min(100, int(confidence))


async def test_smart_synthesizer():
    """Test the smart synthesizer"""
    synthesizer = SmartChatSynthesizer()
    
    test_queries = [
        "What documents do I need for H1B dropbox?",
        "How long does dropbox stamping take?",
        "What is the H1B lottery fee?",
        "Can I travel while my H1B is pending?",
    ]
    
    logger.info("\n" + "="*60)
    logger.info("🧪 TESTING SMART SYNTHESIZER")
    logger.info("="*60)
    
    for query in test_queries:
        logger.info(f"\n❓ Question: {query}")
        logger.info("-" * 60)
        
        result = await synthesizer.synthesize_answer(query)
        
        logger.info(f"✅ Answer (Confidence: {result['confidence']}%):")
        logger.info(result['answer'])
        logger.info(f"\n📚 Sources: {len(result['sources'])}")
        for source in result['sources']:
            if source['type'] == 'official':
                logger.info(f"  📰 {source['title']}")
            else:
                logger.info(f"  💬 Community: {source['title']}")
        logger.info("="*60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_smart_synthesizer())
