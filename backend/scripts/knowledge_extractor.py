"""
Knowledge Extractor - Extract Q&A knowledge from conversations and web sources
Combines 1.5M conversations with authoritative sources like RedBus2US
Uses LOCAL LLM (Ollama) - No API keys needed!
"""

import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import os
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import json
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeExtractor:
    """Extract structured Q&A knowledge from conversations using LOCAL LLM"""
    
    def __init__(self):
        # Use Ollama (local LLM) instead of OpenAI
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model_name = os.getenv('LLM_MODEL', 'llama3.2')  # or mistral, phi, etc.
        self.qdrant = QdrantClient(host=os.getenv('QDRANT_HOST', 'localhost'), port=6333)
        self.encoder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        logger.info(f"🤖 Using LOCAL LLM: {self.model_name} at {self.ollama_host}")
        
        # Knowledge categories
        self.categories = {
            'h1b_documents': 'H1B Visa Documents',
            'h1b_process': 'H1B Visa Process',
            'h1b_timeline': 'H1B Timeline',
            'h1b_fees': 'H1B Fees',
            'dropbox_process': 'Dropbox Stamping',
            'f1_visa': 'F1 Student Visa',
            'b1_b2_visa': 'B1/B2 Tourist Visa',
            'interview_prep': 'Visa Interview Preparation',
            'administrative_processing': '221g / Administrative Processing',
            'visa_denial': 'Visa Denial',
            'policy_changes': 'Recent Policy Changes',
        }
    
    async def call_local_llm(self, prompt: str, system_prompt: str = "") -> str:
        """Call local LLM (Ollama) for text generation"""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:  # Increased timeout to 120s
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": f"{system_prompt}\n\n{prompt}" if system_prompt else prompt,
                        "stream": False,
                        "format": "json",  # Request JSON output
                        "options": {
                            "temperature": 0.1,  # Low for consistent extraction
                            "num_predict": 500,  # Max tokens
                        }
                    }
                )
                
                if response.status_code == 200:
                    llm_response = response.json()['response']
                    # logger.info(f"✅ LLM Response (first 300 chars): {llm_response[:300]}")  # Too verbose
                    return llm_response
                else:
                    logger.error(f"Ollama error: {response.status_code}")
                    logger.error(f"Response body: {response.text[:500]}")
                    return "{}"
                    
        except Exception as e:
            logger.error(f"Error calling local LLM: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return "{}"
    
    async def extract_qa_from_conversation(self, conversation: str, metadata: Dict) -> Optional[Dict]:
        """
        Use LOCAL LLM to extract Q&A pairs from a single conversation
        Returns structured knowledge with category, question, answer, confidence
        """
        try:
            # logger.info(f"📝 Processing conversation (first 150 chars): {conversation[:150]}")  # Too verbose
            
            prompt = f"""Analyze this visa-related conversation and extract knowledge.

Conversation:
{conversation[:2000]}

Extract:
1. Main question being asked (if any)
2. Clear answer provided (if any)
3. Category (h1b_documents, h1b_process, dropbox_process, f1_visa, etc.)
4. Confidence score (0-100) - how complete is the answer?
5. Key information (document lists, timelines, fees, URLs)

Return ONLY valid JSON (no markdown, no backticks):
{{
    "has_qa": true,
    "question": "What documents are needed for H1B dropbox?",
    "answer": "For H1B dropbox, you need: 1. Passport...",
    "category": "h1b_documents",
    "subcategory": "dropbox",
    "confidence": 85,
    "key_facts": ["Passport required", "DS-160 confirmation"],
    "timeline_mentioned": "7-15 days",
    "fees_mentioned": "$185",
    "links": []
}}

If no clear Q&A, return: {{"has_qa": false}}"""

            system_prompt = "You are an expert at extracting structured knowledge from visa conversations. Return ONLY valid JSON."
            
            response_text = await self.call_local_llm(prompt, system_prompt)
            
            # Clean response (remove markdown if present)
            response_text = response_text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()
            
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as je:
                logger.error(f"JSON decode error: {je}")
                logger.error(f"LLM response (first 200 chars): {response_text[:200]}")
                return None
            
            if result.get('has_qa') and result.get('confidence', 0) >= 50:
                # Add metadata
                result['source'] = 'conversation'
                result['timestamp'] = metadata.get('timestamp')
                result['conversation_id'] = metadata.get('id')
                logger.info(f"✅ EXTRACTED Q&A - Q: {result.get('question', '')[:100]} | Conf: {result.get('confidence')}%")
                return result
            else:
                logger.info(f"⏭️  Skipped - has_qa: {result.get('has_qa')}, confidence: {result.get('confidence', 0)}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting Q&A: {type(e).__name__}: {str(e)}")
            return None
    
    async def batch_process_conversations(self, batch_size: int = 100, total_limit: int = 10000):
        """
        Process conversations in batches to extract knowledge
        Start with 10K as prototype, can scale to 1.5M
        """
        logger.info(f"🚀 Starting knowledge extraction from {total_limit} conversations...")
        
        collection_name = "visa_conversations"
        
        # Get conversations from Qdrant
        offset = 0
        processed = 0
        extracted_knowledge = []
        
        while processed < total_limit:
            # Scroll through Qdrant
            results = self.qdrant.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            records, next_offset = results
            
            if not records:
                break
            
            # Process batch
            tasks = []
            for record in records:
                conversation = record.payload.get('text', '')  # Fixed: field is 'text', not 'conversation'
                metadata = {
                    'id': str(record.id),
                    'timestamp': record.payload.get('timestamp'),
                    'category': record.payload.get('primary_category'),
                    'is_question': record.payload.get('is_question'),
                    'location': record.payload.get('location')
                }
                tasks.append(self.extract_qa_from_conversation(conversation, metadata))
            
            # Run in parallel
            batch_results = await asyncio.gather(*tasks)
            
            # Filter and collect
            for result in batch_results:
                if result:
                    extracted_knowledge.append(result)
            
            processed += len(records)
            offset = next_offset
            
            logger.info(f"✅ Processed {processed}/{total_limit} conversations, extracted {len(extracted_knowledge)} Q&A pairs")
        
        return extracted_knowledge
    
    def save_knowledge_base(self, knowledge: List[Dict], output_file: str = "data/knowledge_base.json"):
        """Save extracted knowledge to file"""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(knowledge, f, indent=2, default=str)
        
        logger.info(f"💾 Saved {len(knowledge)} knowledge entries to {output_file}")
    
    def analyze_knowledge_base(self, knowledge: List[Dict]):
        """Analyze the extracted knowledge"""
        stats = {
            'total_entries': len(knowledge),
            'by_category': {},
            'avg_confidence': 0,
            'with_timeline': 0,
            'with_fees': 0,
            'with_links': 0
        }
        
        total_confidence = 0
        
        for entry in knowledge:
            # Count by category
            category = entry.get('category', 'unknown')
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            # Confidence
            total_confidence += entry.get('confidence', 0)
            
            # Features
            if entry.get('timeline_mentioned'):
                stats['with_timeline'] += 1
            if entry.get('fees_mentioned'):
                stats['with_fees'] += 1
            if entry.get('links'):
                stats['with_links'] += 1
        
        stats['avg_confidence'] = total_confidence / len(knowledge) if knowledge else 0
        
        return stats


async def main():
    """Run knowledge extraction prototype"""
    extractor = KnowledgeExtractor()
    
    # Phase 1: Extract from conversations (10K prototype)
    logger.info("📊 Phase 1: Extracting knowledge from conversations...")
    knowledge = await extractor.batch_process_conversations(
        batch_size=100,
        total_limit=10000  # Start with 10K, can scale to 1.5M
    )
    
    # Save results
    extractor.save_knowledge_base(knowledge)
    
    # Analyze
    stats = extractor.analyze_knowledge_base(knowledge)
    
    logger.info("\n" + "="*60)
    logger.info("📈 KNOWLEDGE EXTRACTION RESULTS")
    logger.info("="*60)
    logger.info(f"Total Q&A pairs extracted: {stats['total_entries']}")
    logger.info(f"Average confidence: {stats['avg_confidence']:.1f}%")
    logger.info(f"\n📋 By Category:")
    for cat, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {cat}: {count}")
    logger.info(f"\n✨ Features:")
    logger.info(f"  With timeline info: {stats['with_timeline']}")
    logger.info(f"  With fee info: {stats['with_fees']}")
    logger.info(f"  With links: {stats['with_links']}")
    logger.info("="*60)
    
    # Phase 2: Next step - scrape RedBus2US (placeholder)
    logger.info("\n🌐 Phase 2: Ready to scrape RedBus2US for authoritative content...")
    logger.info("   This will supplement conversation data with official information")


if __name__ == "__main__":
    asyncio.run(main())
