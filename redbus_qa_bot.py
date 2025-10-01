"""
Simple Q&A Bot using RedBus2US H1B Articles
Uses local LLM (Ollama) to answer questions based on scraped content
"""

import json
import logging
from typing import Dict, List
from sentence_transformers import SentenceTransformer
import numpy as np
import httpx
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedBusQABot:
    """Simple Q&A bot using RedBus2US knowledge"""
    
    def __init__(self, articles_file='data/redbus2us_h1b_articles.json'):
        logger.info("🤖 Initializing RedBus Q&A Bot...")
        
        # Load articles
        with open(articles_file, 'r') as f:
            self.articles = json.load(f)
        
        logger.info(f"📚 Loaded {len(self.articles)} H1B articles from RedBus2US")
        
        # Initialize sentence encoder for semantic search
        self.encoder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Pre-compute article embeddings
        self.article_texts = [
            f"{article['title']}\n{article['excerpt']}" 
            for article in self.articles
        ]
        logger.info("🔍 Computing embeddings for semantic search...")
        self.article_embeddings = self.encoder.encode(self.article_texts)
        
        # Ollama settings - use qwen (faster than llama3.2)
        self.ollama_host = "http://localhost:11434"
        self.model_name = "qwen"  # Faster 4B model
        
        logger.info(f"✅ Q&A Bot ready! Using {self.model_name} at {self.ollama_host}")
    
    def find_relevant_articles(self, query: str, top_k: int = 3) -> List[Dict]:
        """Find most relevant articles for a query using semantic search"""
        # Encode query
        query_embedding = self.encoder.encode([query])[0]
        
        # Calculate similarities
        similarities = np.dot(self.article_embeddings, query_embedding)
        
        # Get top-k most similar articles
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        relevant_articles = []
        for idx in top_indices:
            article = self.articles[idx].copy()
            article['relevance_score'] = float(similarities[idx])
            relevant_articles.append(article)
        
        return relevant_articles
    
    async def generate_answer(self, query: str) -> Dict:
        """Generate answer using local LLM and relevant articles"""
        logger.info(f"❓ Question: {query}")
        
        # Find relevant articles
        relevant_articles = self.find_relevant_articles(query, top_k=3)
        
        if not relevant_articles:
            return {
                "answer": "I don't have information about that in the RedBus2US H1B articles.",
                "sources": [],
                "confidence": 0
            }
        
        # Build context from articles (simplified for faster processing)
        context = "H1B Visa Information:\n\n"
        for i, article in enumerate(relevant_articles, 1):
            context += f"{i}. {article['title']}\n{article['excerpt'][:200]}...\n\n"
        
        # Create simplified prompt for faster LLM response
        prompt = f"""Answer this H1B visa question using the information below.

{context}

Question: {query}

Provide a clear, direct answer with specific details (fees, dates, timelines). Be concise.

Answer:"""

        try:
            # Call local LLM with shorter response and higher timeout
            async with httpx.AsyncClient(timeout=120.0) as client:  # 2 min timeout
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,  # Lower for more focused answers
                            "num_predict": 300,  # Shorter responses
                        }
                    }
                )
                
                if response.status_code == 200:
                    answer = response.json()['response']
                    logger.info(f"✅ Generated answer ({len(answer)} chars)")
                else:
                    logger.error(f"LLM error status: {response.status_code}")
                    logger.error(f"Response: {response.text[:500]}")
                    answer = "Sorry, I encountered an error generating the answer."
            
            return {
                "answer": answer,
                "sources": [
                    {
                        "title": article['title'],
                        "url": article['url'],
                        "date": article['published_date'],
                        "relevance": f"{article['relevance_score']:.2f}"
                    }
                    for article in relevant_articles
                ],
                "confidence": int(relevant_articles[0]['relevance_score'] * 100)
            }
            
        except Exception as e:
            import traceback
            logger.error(f"Error generating answer: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "answer": f"Error: {type(e).__name__}: {str(e)}",
                "sources": [
                    {
                        "title": article['title'],
                        "url": article['url'],
                        "date": article['published_date'],
                        "relevance": f"{article['relevance_score']:.2f}"
                    }
                    for article in relevant_articles
                ],
                "confidence": 0
            }


async def main():
    """Test the Q&A bot"""
    bot = RedBusQABot()
    
    test_questions = [
        "What is the $100K fee about?",
        "When does the H1B 2026 season start?",
        "What is the H1B registration fee for 2026?",
    ]
    
    print("\n" + "="*70)
    print("🤖 RedBus2US H1B Q&A Bot - Test")
    print("="*70 + "\n")
    
    import asyncio as aio
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n❓ Q{i}: {question}")
        print("-" * 70)
        
        result = await bot.generate_answer(question)
        
        print(f"💡 A: {result['answer']}\n")
        print(f"📚 Sources:")
        for source in result['sources']:
            print(f"   • {source['title']}")
            print(f"     {source['url']}")
        print(f"\n🎯 Confidence: {result['confidence']}%")
        print("="*70)
        
        # Delay between questions to avoid overwhelming Ollama
        if i < len(test_questions):
            await aio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
