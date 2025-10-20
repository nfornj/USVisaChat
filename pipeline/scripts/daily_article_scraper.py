#!/usr/bin/env python3
"""
Daily Article Scraper Pipeline
Automatically scrapes new RedBus2US articles, organizes them, summarizes them, and updates the vector database.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import shutil

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from backend.services.llm_service import llm_service

# Configure logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True, parents=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"daily_scraper_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DailyArticlePipeline:
    """Daily pipeline for scraping, organizing, summarizing, and indexing articles."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.backend_dir = self.project_root / "backend"
        self.data_dir = self.project_root / "data"
        self.pipeline_config = self.load_config()
        
        # Directories
        self.raw_dir = self.data_dir / "redbus2us_raw"
        self.organized_dir = self.data_dir / "redbus2us_organized" 
        self.summaries_dir = self.data_dir / "redbus2us_summaries"
        
        # Scripts paths
        self.scraper_script = self.project_root / "pipeline" / "article_processing" / "comprehensive_redbus_scraper.py"
        self.organizer_script = self.project_root / "pipeline" / "article_processing" / "organize_articles.py"
        self.summarizer_script = self.project_root / "pipeline" / "article_processing" / "article_summarizer.py"
        self.vector_script = self.backend_dir / "scripts" / "load_redbus_to_qdrant.py"
        
    def load_config(self):
        """Load pipeline configuration."""
        config_file = Path(__file__).parent.parent / "config" / "pipeline_config.json"
        
        # Default configuration
        default_config = {
            "scraping": {
                "max_articles_per_run": 50,
                "categories": [
                    "h1b-visa", "f1-visa", "h4-visa", "green-card", 
                    "us-immigration", "policy-updates", "fees", 
                    "documents", "interview", "process-timeline"
                ],
                "lookback_days": 7,
                "rate_limit_seconds": 2
            },
            "processing": {
                "enable_organization": True,
                "enable_summarization": True,
                "enable_vector_indexing": True,
                "batch_size": 10
            },
            "notifications": {
                "log_level": "INFO",
                "email_alerts": False
            }
        }
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            # Merge with defaults
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
        else:
            config = default_config
            # Create config file
            config_file.parent.mkdir(exist_ok=True, parents=True)
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"📁 Created default config: {config_file}")
        
        return config

    async def run_daily_pipeline(self):
        """Execute the complete daily pipeline."""
        logger.info("🚀 Starting Daily Article Pipeline")
        
        pipeline_stats = {
            "start_time": datetime.now().isoformat(),
            "stages": {},
            "total_new_articles": 0,
            "status": "running"
        }
        
        try:
            # Stage 1: Scrape new articles
            logger.info("📥 Stage 1: Scraping new articles...")
            scraping_stats = await self.scrape_new_articles()
            pipeline_stats["stages"]["scraping"] = scraping_stats
            pipeline_stats["total_new_articles"] = scraping_stats.get("new_articles_count", 0)
            
            if pipeline_stats["total_new_articles"] == 0:
                logger.info("✅ No new articles found. Pipeline completed.")
                pipeline_stats["status"] = "completed_no_new_articles"
                self.save_pipeline_stats(pipeline_stats)
                return pipeline_stats
            
            # Stage 2: Organize articles
            if self.pipeline_config["processing"]["enable_organization"]:
                logger.info("📁 Stage 2: Organizing articles...")
                organization_stats = await self.organize_articles()
                pipeline_stats["stages"]["organization"] = organization_stats
            
            # Stage 3: Summarize articles
            if self.pipeline_config["processing"]["enable_summarization"]:
                logger.info("📝 Stage 3: Summarizing articles...")
                summarization_stats = await self.summarize_articles()
                pipeline_stats["stages"]["summarization"] = summarization_stats
            
            # Stage 4: Update vector database
            if self.pipeline_config["processing"]["enable_vector_indexing"]:
                logger.info("🔍 Stage 4: Updating vector database...")
                vector_stats = await self.update_vector_database()
                pipeline_stats["stages"]["vector_indexing"] = vector_stats
            
            pipeline_stats["status"] = "completed_success"
            pipeline_stats["end_time"] = datetime.now().isoformat()
            
            logger.info(f"✅ Daily pipeline completed successfully!")
            logger.info(f"📊 Processed {pipeline_stats['total_new_articles']} new articles")
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            pipeline_stats["status"] = "failed"
            pipeline_stats["error"] = str(e)
            pipeline_stats["end_time"] = datetime.now().isoformat()
            raise
        
        finally:
            self.save_pipeline_stats(pipeline_stats)
        
        return pipeline_stats

    async def scrape_new_articles(self):
        """Scrape new articles from RedBus2US."""
        try:
            # Calculate lookback date
            lookback_days = self.pipeline_config["scraping"]["lookback_days"]
            since_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            
            # Run comprehensive scraper
            cmd = [
                "uv", "run", "python", str(self.scraper_script),
                "--since", since_date,
                "--max-articles", str(self.pipeline_config["scraping"]["max_articles_per_run"]),
                "--rate-limit", str(self.pipeline_config["scraping"]["rate_limit_seconds"])
            ]
            
            logger.info(f"🔄 Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Scraper failed: {result.stderr}")
            
            # Parse output for stats
            output = result.stdout
            new_articles_count = self.extract_number_from_output(output, "scraped articles")
            
            return {
                "success": True,
                "new_articles_count": new_articles_count,
                "since_date": since_date,
                "output": output
            }
            
        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            return {"success": False, "error": str(e), "new_articles_count": 0}

    async def organize_articles(self):
        """Organize scraped articles."""
        try:
            cmd = ["uv", "run", "python", str(self.organizer_script)]
            logger.info(f"🔄 Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Organization failed: {result.stderr}")
            
            return {"success": True, "output": result.stdout}
            
        except Exception as e:
            logger.error(f"❌ Organization failed: {e}")
            return {"success": False, "error": str(e)}

    async def summarize_articles(self):
        """Summarize organized articles."""
        try:
            cmd = ["uv", "run", "python", str(self.summarizer_script)]
            logger.info(f"🔄 Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Summarization failed: {result.stderr}")
            
            # Extract stats
            output = result.stdout
            summaries_count = self.extract_number_from_output(output, "summaries")
            
            return {
                "success": True, 
                "summaries_count": summaries_count,
                "output": output
            }
            
        except Exception as e:
            logger.error(f"❌ Summarization failed: {e}")
            return {"success": False, "error": str(e)}

    async def update_vector_database(self):
        """Update vector database with new summaries."""
        try:
            cmd = ["uv", "run", "python", str(self.vector_script)]
            logger.info(f"🔄 Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Vector indexing failed: {result.stderr}")
            
            # Extract stats
            output = result.stdout
            vectors_count = self.extract_number_from_output(output, "vectors")
            
            return {
                "success": True,
                "vectors_indexed": vectors_count,
                "output": output
            }
            
        except Exception as e:
            logger.error(f"❌ Vector indexing failed: {e}")
            return {"success": False, "error": str(e)}

    def extract_number_from_output(self, output: str, keyword: str) -> int:
        """Extract a number from script output based on keyword."""
        try:
            lines = output.split('\n')
            for line in lines:
                if keyword.lower() in line.lower():
                    # Extract numbers from the line
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        return int(numbers[0])
            return 0
        except:
            return 0

    def save_pipeline_stats(self, stats: dict):
        """Save pipeline statistics."""
        stats_dir = self.project_root / "pipeline" / "logs" / "stats"
        stats_dir.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        stats_file = stats_dir / f"pipeline_stats_{timestamp}.json"
        
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        # Also save as latest
        latest_file = stats_dir / "latest_pipeline_stats.json"
        with open(latest_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"📊 Pipeline stats saved: {stats_file}")

async def main():
    """Run the daily pipeline."""
    pipeline = DailyArticlePipeline()
    stats = await pipeline.run_daily_pipeline()
    
    # Print summary
    print("\n" + "="*80)
    print("📊 DAILY PIPELINE SUMMARY")
    print("="*80)
    print(f"Status: {stats['status']}")
    print(f"New Articles: {stats.get('total_new_articles', 0)}")
    print(f"Duration: {stats.get('end_time', 'Running...')}")
    
    if stats.get('stages'):
        print("\n📈 Stage Results:")
        for stage, result in stats['stages'].items():
            status = "✅" if result.get('success') else "❌"
            print(f"  {status} {stage.title()}")
    
    print("="*80)
    return stats

if __name__ == "__main__":
    asyncio.run(main())