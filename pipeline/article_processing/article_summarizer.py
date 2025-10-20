"""
Summarize RedBus2US articles using local LLM for vector database storage.
Creates comprehensive summaries that capture all key information.
"""

import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))
from backend.services.llm_service import llm_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArticleSummarizer:
    """Summarizes articles using local LLM."""
    
    def __init__(self):
        self.data_dir = Path("data/redbus2us_organized")
        self.summaries_dir = Path("data/redbus2us_summaries")
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        
        # Improved prompts for better fact preservation
        self.prompts = {
            'general': """
                EXTRACT AND PRESERVE ALL FACTUAL INFORMATION from this visa article.
                
                MANDATORY: You MUST preserve EVERY date, fee amount, document name, deadline, and process step mentioned.
                
                FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:
                
                ## FACTUAL SUMMARY
                
                **MAIN TOPIC:** [One clear sentence describing the article's focus]
                
                **KEY FACTS:**
                • DATES: [List ALL dates mentioned - format: Month DD, YYYY or MM/DD/YYYY]
                • FEES: [List ALL dollar amounts, costs, and fee types with exact numbers]
                • DEADLINES: [List ALL deadlines, timelines, and time periods]
                • DOCUMENTS: [List ALL document names, forms, and requirements]
                • PROCESSES: [List ALL step-by-step procedures in order]
                • REQUIREMENTS: [List ALL eligibility criteria and conditions]
                
                **DETAILED SUMMARY:**
                [2-3 paragraphs that include ALL the facts listed above, maintaining exact dates, amounts, and document names. Every fact must appear in both the KEY FACTS section and this summary.]
                
                **IMPORTANT WARNINGS/NOTES:**
                • [List any warnings, exceptions, or critical information]
                
                **SOURCES:**
                • [List any official sources, websites, or authorities mentioned]
                
                ARTICLE TO ANALYZE:
                {content}
                
                CRITICAL: Double-check that EVERY date, fee, and document name from the original article appears in your summary. Do not paraphrase numbers or dates - use exact values.
                """,
            
            'process_timeline': """
                EXTRACT COMPLETE PROCESS TIMELINE with ALL factual details preserved.
                
                FORMAT EXACTLY AS FOLLOWS:
                
                ## PROCESS TIMELINE SUMMARY
                
                **PROCESS NAME:** [Title of the process or procedure]
                
                **TIMELINE OVERVIEW:**
                • Total Duration: [Exact time period if mentioned]
                • Key Deadlines: [List ALL dates and deadlines with exact dates]
                
                **STEP-BY-STEP PROCESS:**
                1. **Step Name:** [Brief description]
                   - Required Documents: [List ALL documents for this step]
                   - Timeline: [Exact timeframe or deadline]
                   - Fees: [Exact amounts if any]
                   - Key Requirements: [Specific conditions or criteria]
                
                [Continue for each step...]
                
                **CRITICAL DATES:**
                • [List ALL dates mentioned with exact format: Month DD, YYYY]
                
                **ALL FEES AND COSTS:**
                • [List every fee amount mentioned with exact dollar figures]
                
                **DOCUMENT CHECKLIST:**
                • [Complete list of ALL documents mentioned]
                
                **WARNINGS & COMMON ISSUES:**
                • [List all warnings, potential problems, or exceptions]
                
                ARTICLE TO ANALYZE:
                {content}
                
                CRITICAL: Preserve EVERY date, fee amount, and document name exactly as written.
                """,
            
            'policy_updates': """
                EXTRACT ALL POLICY CHANGE DETAILS with complete factual accuracy.
                
                FORMAT EXACTLY AS FOLLOWS:
                
                ## POLICY UPDATE SUMMARY
                
                **POLICY/RULE CHANGED:** [Exact name/title of policy or regulation]
                
                **EFFECTIVE DATE:** [Exact date when change takes effect - must be exact format]
                
                **WHO IS AFFECTED:**
                • [List ALL visa categories, applicant types, or groups affected]
                
                **SPECIFIC CHANGES:**
                • OLD RULE: [What it was before]
                • NEW RULE: [What it is now]
                • KEY DIFFERENCES: [Specific changes in requirements, processes, or rules]
                
                **IMPACT BY VISA TYPE:**
                • H1B: [Specific impact if mentioned]
                • F1: [Specific impact if mentioned]
                • [Continue for each visa type mentioned...]
                
                **ACTION ITEMS:**
                • [List ALL actions visa holders must take]
                • [Include any deadlines or timeframes]
                
                **CRITICAL DATES:**
                • [ALL dates mentioned in exact format: Month DD, YYYY]
                
                **FEES/COST CHANGES:**
                • [Any fee changes with exact old and new amounts]
                
                **OFFICIAL SOURCES:**
                • [Government agencies, official websites, or authorities cited]
                
                ARTICLE TO ANALYZE:
                {content}
                
                CRITICAL: Preserve exact dates, fee amounts, and policy names. Do not paraphrase official terminology.
                """,
            
            'fees': """
                EXTRACT ALL FEE INFORMATION with exact dollar amounts preserved.
                
                FORMAT EXACTLY AS FOLLOWS:
                
                ## VISA FEES SUMMARY
                
                **MAIN TOPIC:** [What fees this article covers]
                
                **ALL FEES AND AMOUNTS:**
                • [Fee Type 1]: $[Exact Amount] - [What it covers]
                • [Fee Type 2]: $[Exact Amount] - [What it covers]
                [Continue for EVERY fee mentioned...]
                
                **FEE CHANGES (if any):**
                • OLD FEE: $[Amount] → NEW FEE: $[Amount] (Effective: [Date])
                
                **PAYMENT REQUIREMENTS:**
                • Payment Methods: [List ALL accepted methods]
                • Payment Timing: [When payments are due]
                • Payment Location: [Where to pay]
                
                **ADDITIONAL COSTS:**
                • [List any extra charges, processing fees, or optional services]
                
                **REFUND POLICIES:**
                • [List ALL refund conditions and policies]
                
                **CRITICAL DATES:**
                • [ALL payment deadlines and effective dates in exact format]
                
                **OFFICIAL SOURCES:**
                • [Government fee schedules, official websites mentioned]
                
                ARTICLE TO ANALYZE:
                {content}
                
                CRITICAL: Every dollar amount must be preserved exactly. Do not round or approximate fees.
                """,
            
            'documents': """
                EXTRACT ALL DOCUMENT REQUIREMENTS with complete specifications preserved.
                
                FORMAT EXACTLY AS FOLLOWS:
                
                ## DOCUMENT REQUIREMENTS SUMMARY
                
                **PROCESS/APPLICATION:** [What these documents are for]
                
                **REQUIRED DOCUMENTS CHECKLIST:**
                • [Document Name 1]: [Exact specifications, format, or requirements]
                • [Document Name 2]: [Exact specifications, format, or requirements]
                [Continue for EVERY document mentioned...]
                
                **DOCUMENT SPECIFICATIONS:**
                • Format Requirements: [Digital, paper, notarized, etc.]
                • Size/Page Limits: [Any size or length requirements]
                • Language Requirements: [Translation needs, certification]
                • Validity Periods: [How current documents must be]
                
                **SPECIAL CONDITIONS:**
                • [List ANY special requirements or exceptions]
                • [Country-specific requirements]
                • [Conditional requirements based on circumstances]
                
                **PREPARATION STEPS:**
                1. [Step-by-step preparation process if mentioned]
                
                **SUBMISSION REQUIREMENTS:**
                • Where to Submit: [Exact locations or addresses]
                • How to Submit: [Mail, online, in-person]
                • Submission Deadlines: [Exact dates if mentioned]
                
                **COMMON MISTAKES TO AVOID:**
                • [List ALL warnings about document errors]
                
                **PROCESSING TIMELINE:**
                • [How long document review takes]
                • [Any expedited processing options]
                
                ARTICLE TO ANALYZE:
                {content}
                
                CRITICAL: Preserve exact document names (I-20, DS-160, Form I-94, etc.) and all specifications exactly.
                """
        }
    
    async def summarize_article(self, article: Dict) -> Dict:
        """Summarize a single article using appropriate prompt."""
        try:
            # Select appropriate prompt based on article type
            article_type = article.get('article_type', 'general')
            prompt = self.prompts.get(article_type, self.prompts['general'])
            
            # Get article content
            content = article.get('content', '')
            if not content:
                logger.warning(f"⚠️ No content for article: {article.get('title', 'No title')}")
                return None
            
            # Generate summary using LLM with improved settings
            summary_response = await llm_service.generate_response(
                prompt=prompt.format(content=content),
                system_prompt="You are a precise visa information extraction specialist. Your job is to preserve EVERY factual detail (dates, fees, document names, deadlines) exactly as written. Never paraphrase numbers, dates, or official terminology. Extract facts first, then summarize while maintaining all specific details.",
                temperature=0.05,  # Even lower temperature for maximum factual accuracy
                max_tokens=600     # Increased token limit for detailed summaries
            )
            
            # Create summary object
            summary = {
                'title': article.get('title', 'No title'),
                'url': article.get('url', ''),
                'published_date': article.get('published_date', ''),
                'category': article.get('category', 'Uncategorized'),
                'visa_type': article.get('visa_category', 'General'),
                'article_type': article_type,
                'summary': summary_response,
                'key_points': article.get('key_points', []),
                'has_timeline': article.get('has_timeline', False),
                'has_fees': article.get('has_fees', False),
                'has_documents': article.get('has_documents', False),
                'metadata': {
                    'summarized_at': datetime.now().isoformat(),
                    'original_word_count': article.get('word_count', 0),
                    'summary_word_count': len(summary_response.split())
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error summarizing article: {e}")
            return None
    
    async def process_organized_articles(self):
        """Process all organized articles and create summaries."""
        # Find the most recent organized dataset
        input_files = list(self.data_dir.glob("organized_complete_*.json"))
        if not input_files:
            logger.error("❌ No organized articles found!")
            return
        
        latest_file = max(input_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"📂 Found latest organized dataset: {latest_file}")
        
        # Load organized articles
        with open(latest_file, 'r', encoding='utf-8') as f:
            organized = json.load(f)
        
        # Initialize statistics
        stats = {
            'total_processed': 0,
            'successful_summaries': 0,
            'failed_summaries': 0,
            'by_category': {},
            'by_visa_type': {},
            'by_year': {}
        }
        
        # Process articles by year and month
        summaries = {}
        for year in organized:
            summaries[year] = {}
            stats['by_year'][year] = 0
            
            for month in organized[year]:
                summaries[year][month] = {}
                
                for category in organized[year][month]:
                    if category not in stats['by_category']:
                        stats['by_category'][category] = 0
                    
                    summaries[year][month][category] = {}
                    
                    for visa_type in organized[year][month][category]:
                        if visa_type not in stats['by_visa_type']:
                            stats['by_visa_type'][visa_type] = 0
                        
                        articles = organized[year][month][category][visa_type]
                        summaries[year][month][category][visa_type] = []
                        
                        logger.info(f"📝 Processing {len(articles)} articles from {year}/{month} - {category} - {visa_type}")
                        
                        for article in articles:
                            stats['total_processed'] += 1
                            
                            summary = await self.summarize_article(article)
                            if summary:
                                summaries[year][month][category][visa_type].append(summary)
                                stats['successful_summaries'] += 1
                                stats['by_category'][category] += 1
                                stats['by_visa_type'][visa_type] += 1
                                stats['by_year'][year] += 1
                            else:
                                stats['failed_summaries'] += 1
                            
                            # Progress update
                            if stats['total_processed'] % 10 == 0:
                                logger.info(f"✅ Processed {stats['total_processed']} articles...")
        
        # Save summaries and stats
        self.save_summaries(summaries, stats)
    
    def save_summaries(self, summaries: Dict, stats: Dict):
        """Save summaries and statistics."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save complete summaries dataset
        complete_file = self.summaries_dir / f"summaries_complete_{timestamp}.json"
        with open(complete_file, 'w', encoding='utf-8') as f:
            json.dump(summaries, f, indent=2, ensure_ascii=False)
        
        # Save by year
        for year in summaries:
            year_file = self.summaries_dir / f"summaries_{year}_{timestamp}.json"
            with open(year_file, 'w', encoding='utf-8') as f:
                json.dump(summaries[year], f, indent=2, ensure_ascii=False)
        
        # Save statistics
        stats_file = self.summaries_dir / f"summarization_stats_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        # Generate summary report
        report_file = self.summaries_dir / f"summarization_report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# RedBus2US Articles Summarization Report\n\n")
            
            f.write("## 📊 Overall Statistics\n\n")
            f.write(f"- Total articles processed: {stats['total_processed']}\n")
            f.write(f"- Successful summaries: {stats['successful_summaries']}\n")
            f.write(f"- Failed summaries: {stats['failed_summaries']}\n\n")
            
            f.write("## 📅 Summaries by Year\n\n")
            for year in sorted(stats['by_year'].keys()):
                f.write(f"- {year}: {stats['by_year'][year]} summaries\n")
            f.write("\n")
            
            f.write("## 📋 Summaries by Category\n\n")
            for category in sorted(stats['by_category'].keys()):
                f.write(f"- {category}: {stats['by_category'][category]} summaries\n")
            f.write("\n")
            
            f.write("## 🎯 Summaries by Visa Type\n\n")
            for visa_type in sorted(stats['by_visa_type'].keys()):
                f.write(f"- {visa_type}: {stats['by_visa_type'][visa_type]} summaries\n")
            f.write("\n")
            
            f.write("## 📁 Generated Files\n\n")
            f.write(f"- Complete dataset: {complete_file.name}\n")
            f.write(f"- Statistics: {stats_file.name}\n")
            f.write(f"- Year-specific files: {len(summaries)} files\n")
        
        logger.info("\n" + "="*80)
        logger.info("✅ Summarization completed successfully!")
        logger.info(f"📊 Total processed: {stats['total_processed']}")
        logger.info(f"✅ Successful: {stats['successful_summaries']}")
        logger.info(f"❌ Failed: {stats['failed_summaries']}")
        logger.info(f"📁 Data saved to: {self.summaries_dir}")
        logger.info(f"📄 Report generated: {report_file}")
        logger.info("="*80)

async def main():
    """Run the article summarizer."""
    summarizer = ArticleSummarizer()
    await summarizer.process_organized_articles()

if __name__ == "__main__":
    asyncio.run(main())
