"""
Master Knowledge Extraction Pipeline
Runs the complete pipeline to build intelligent knowledge base
"""

import asyncio
import logging
from knowledge_extractor import KnowledgeExtractor
from redbus2us_scraper import RedBus2UScraper
from smart_chat_synthesizer import SmartChatSynthesizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_full_pipeline():
    """Run the complete knowledge extraction pipeline"""
    
    logger.info("\n" + "="*70)
    logger.info("🚀 VISA KNOWLEDGE EXTRACTION PIPELINE - PROTOTYPE")
    logger.info("="*70)
    logger.info("\nGoal: Transform 1.5M conversations into actionable knowledge")
    logger.info("Prototype: Processing 10K conversations + RedBus2US content\n")
    
    # PHASE 1: Extract knowledge from conversations
    logger.info("\n" + "─"*70)
    logger.info("📊 PHASE 1: Extract Q&A Knowledge from Conversations")
    logger.info("─"*70)
    logger.info("Processing first 100 conversations (DEMO MODE)...")
    logger.info("Using LOCAL LLM (Llama 3.2) to extract structured Q&A pairs\n")
    
    extractor = KnowledgeExtractor()
    conversation_knowledge = await extractor.batch_process_conversations(
        batch_size=10,  # Increased batch size
        total_limit=100  # Process 100 conversations to see patterns
    )
    
    extractor.save_knowledge_base(conversation_knowledge)
    conv_stats = extractor.analyze_knowledge_base(conversation_knowledge)
    
    logger.info("\n✅ Phase 1 Complete:")
    logger.info(f"   Extracted: {conv_stats['total_entries']} Q&A pairs")
    logger.info(f"   Avg Confidence: {conv_stats['avg_confidence']:.1f}%")
    logger.info(f"   Top Categories: {list(conv_stats['by_category'].keys())[:3]}")
    
    # PHASE 2: Scrape RedBus2US for authoritative content (SKIPPED FOR DEMO)
    logger.info("\n" + "─"*70)
    logger.info("🌐 PHASE 2: Scrape RedBus2US Official Content (SKIPPED)")
    logger.info("─"*70)
    logger.info("Skipping web scraping in demo mode to focus on LLM extraction\n")
    
    # PHASE 3: Test smart synthesis (SKIPPED IN DEMO MODE)
    if False:  # Skip for demo
        logger.info("\n" + "─"*70)
        logger.info("🧠 PHASE 3: Test Smart Answer Synthesis")
        logger.info("─"*70)
        logger.info("Testing knowledge-based answers vs. conversation snippets\n")
        
        synthesizer = SmartChatSynthesizer()
        
        test_queries = [
            "What documents do I need for H1B dropbox in India?",
            "How long does H1B dropbox take?",
            "What is the H1B fee for 2025?",
        ]
        
        for query in test_queries:
            logger.info(f"\n❓ Test Query: \"{query}\"")
            logger.info("   Searching knowledge base...")
            
            result = await synthesizer.synthesize_answer(query)
            
            logger.info(f"   ✅ Confidence: {result['confidence']}%")
            logger.info(f"   📚 Sources: {len(result['sources'])} ({len([s for s in result['sources'] if s['type']=='official'])} official)")
            logger.info(f"\n   💬 Answer Preview:")
            preview = result['answer'][:200] + "..." if len(result['answer']) > 200 else result['answer']
            for line in preview.split('\n'):
                logger.info(f"      {line}")
    
    # FINAL SUMMARY
    logger.info("\n" + "="*70)
    logger.info("📈 DEMO RESULTS SUMMARY")
    logger.info("="*70)
    logger.info(f"\n📊 Extraction Results:")
    logger.info(f"   Processed: 100 conversations")
    logger.info(f"   Extracted Q&As: {conv_stats['total_entries']}")
    logger.info(f"   Avg Confidence: {conv_stats['avg_confidence']:.1f}%")
    
    logger.info(f"\n📂 Categories Found:")
    for category, count in list(conv_stats['by_category'].items())[:5]:
        logger.info(f"   - {category}: {count} entries")
    
    logger.info(f"\n💾 Output File:")
    logger.info(f"   data/knowledge_base.json")
    
    logger.info("\n" + "="*70)
    logger.info("🎉 DEMO COMPLETE - Review LLM responses above!")
    logger.info("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_full_pipeline())



