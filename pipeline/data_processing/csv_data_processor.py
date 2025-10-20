"""
CSV-Based Data Processing Pipeline - NO DATABASE REQUIRED
Processes CSV files directly without needing PostgreSQL or any database
"""

import asyncio
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import json
import csv
from dataclasses import dataclass, asdict
import logging
from collections import defaultdict
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ProcessingConfig:
    """Configuration for the data processing pipeline."""
    chunk_size: int = 100000  # Messages per chunk file
    session_time_window_minutes: int = 60  # Time window for sessionization
    min_messages_per_session: int = 2  # Minimum messages to form a session
    min_qa_confidence: float = 0.6  # Minimum confidence for Q&A pairs
    data_dir: Path = Path("data")

class CSVDataProcessor:
    """Standalone CSV-based data processing pipeline - NO DATABASE REQUIRED."""
    
    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ProcessingConfig()
        self.data_dir = Path(self.config.data_dir)
        
        # Ensure directories exist
        self.raw_dir = self.data_dir / "conversations" / "raw"
        self.chunks_dir = self.data_dir / "conversations" / "chunks"
        self.sessions_dir = self.data_dir / "conversations" / "sessions"
        self.topics_dir = self.data_dir / "conversations" / "topics"
        self.embeddings_dir = self.data_dir / "embeddings"
        self.exports_dir = self.data_dir.parent / "exports"
        
        # Create directories
        for dir_path in [self.raw_dir, self.chunks_dir, self.sessions_dir, 
                        self.topics_dir, self.embeddings_dir, self.exports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def step1_preprocessing_chunking(self, csv_files: List[Path] = None) -> List[Path]:
        """
        Step 1: Pre-processing & Chunking
        Process existing CSV files and break into manageable chunks
        """
        logger.info("Starting Step 1: CSV Pre-processing & Chunking")
        
        if not csv_files:
            # Look for CSV files in raw directory
            csv_files = list(self.raw_dir.glob("*.csv"))
            if not csv_files:
                logger.error("No CSV files found in data/conversations/raw/")
                logger.info("Please add your CSV files to data/conversations/raw/ first")
                return []
        
        chunk_files = []
        
        for csv_file in csv_files:
            logger.info(f"Processing CSV file: {csv_file}")
            
            try:
                # Read CSV file
                df = pd.read_csv(csv_file)
                logger.info(f"Loaded {len(df)} messages from {csv_file}")
                
                # Ensure required columns exist
                required_columns = ['content', 'timestamp']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    logger.warning(f"Missing columns {missing_columns} in {csv_file}")
                    # Create missing columns with defaults
                    if 'content' not in df.columns and 'message' in df.columns:
                        df['content'] = df['message']
                    if 'content' not in df.columns and 'text' in df.columns:
                        df['content'] = df['text']
                    if 'timestamp' not in df.columns and 'date' in df.columns:
                        df['timestamp'] = df['date']
                    if 'timestamp' not in df.columns:
                        df['timestamp'] = datetime.now().isoformat()
                
                # Clean and standardize data
                df = df.dropna(subset=['content'])  # Remove empty messages
                df['content'] = df['content'].astype(str)
                
                # Add missing columns with defaults
                if 'message_id' not in df.columns:
                    df['message_id'] = range(1, len(df) + 1)
                if 'chat_id' not in df.columns:
                    df['chat_id'] = 1
                if 'user_id' not in df.columns:
                    df['user_id'] = df.get('from_id', range(1, len(df) + 1))
                if 'username' not in df.columns:
                    df['username'] = df.get('from', 'anonymous')
                
                # Sort by timestamp
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
                
                # Break into chunks
                total_messages = len(df)
                chunk_num = 0
                
                for start_idx in range(0, total_messages, self.config.chunk_size):
                    end_idx = min(start_idx + self.config.chunk_size, total_messages)
                    chunk_df = df.iloc[start_idx:end_idx].copy()
                    
                    # Convert timestamp back to ISO string for JSON serialization
                    chunk_df['timestamp'] = chunk_df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                    
                    # Save chunk file
                    chunk_filename = f"{csv_file.stem}_chunk_{chunk_num:04d}.csv"
                    chunk_path = self.chunks_dir / chunk_filename
                    
                    chunk_df.to_csv(chunk_path, index=False)
                    chunk_files.append(chunk_path)
                    
                    logger.info(f"Created chunk: {chunk_filename} ({len(chunk_df)} messages)")
                    chunk_num += 1
            
            except Exception as e:
                logger.error(f"Error processing {csv_file}: {e}")
                continue
        
        # Create metadata
        metadata = {
            'processing_date': datetime.utcnow().isoformat(),
            'chunk_size': self.config.chunk_size,
            'total_chunks': len(chunk_files),
            'source_files': [str(f) for f in csv_files],
            'chunk_files': [str(f) for f in chunk_files]
        }
        
        metadata_path = self.chunks_dir / "processing_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Step 1 completed: Created {len(chunk_files)} chunk files")
        return chunk_files
    
    async def step2_sessionization(self, chunk_files: List[Path] = None) -> List[Path]:
        """Step 2: Sessionization - NO DATABASE REQUIRED"""
        logger.info("Starting Step 2: Sessionization")
        
        if not chunk_files:
            chunk_files = list(self.chunks_dir.glob("*.csv"))
        
        session_files = []
        
        for chunk_file in chunk_files:
            logger.info(f"Sessionizing chunk: {chunk_file}")
            
            try:
                df = pd.read_csv(chunk_file)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
                
                sessions = []
                
                for chat_id, chat_messages in df.groupby('chat_id'):
                    chat_messages = chat_messages.sort_values('timestamp')
                    current_session = []
                    session_id = str(uuid.uuid4())
                    
                    for idx, message in chat_messages.iterrows():
                        # Start new session if time gap is too large
                        if (current_session and 
                            (message['timestamp'] - current_session[-1]['timestamp']).total_seconds() 
                            > self.config.session_time_window_minutes * 60):
                            
                            if len(current_session) >= self.config.min_messages_per_session:
                                session_data = {
                                    'session_id': session_id,
                                    'chat_id': chat_id,
                                    'start_time': current_session[0]['timestamp'].isoformat(),
                                    'end_time': current_session[-1]['timestamp'].isoformat(),
                                    'message_count': len(current_session),
                                    'messages': current_session
                                }
                                sessions.append(session_data)
                            
                            current_session = []
                            session_id = str(uuid.uuid4())
                        
                        # Add message to current session
                        current_session.append({
                            'message_id': message['message_id'],
                            'user_id': message.get('user_id', 'unknown'),
                            'username': message.get('username', 'anonymous'),
                            'content': message['content'],
                            'timestamp': message['timestamp'],
                        })
                    
                    # Don't forget the last session
                    if len(current_session) >= self.config.min_messages_per_session:
                        session_data = {
                            'session_id': session_id,
                            'chat_id': chat_id,
                            'start_time': current_session[0]['timestamp'].isoformat(),
                            'end_time': current_session[-1]['timestamp'].isoformat(),
                            'message_count': len(current_session),
                            'messages': current_session
                        }
                        sessions.append(session_data)
                
                # Save sessions file
                session_filename = chunk_file.stem + "_sessions.jsonl"
                session_path = self.sessions_dir / session_filename
                
                with open(session_path, 'w', encoding='utf-8') as f:
                    for session in sessions:
                        f.write(json.dumps(session, ensure_ascii=False, default=str) + '\n')
                
                session_files.append(session_path)
                logger.info(f"Created session file: {session_path} ({len(sessions)} sessions)")
            
            except Exception as e:
                logger.error(f"Error processing {chunk_file}: {e}")
                continue
        
        logger.info(f"Step 2 completed: Created {len(session_files)} session files")
        return session_files
    
    def classify_topic_simple(self, text: str) -> Tuple[str, float]:
        """Simple topic classification without ML dependencies."""
        text_lower = text.lower()
        
        visa_keywords = {
            'appointment_booking': ['appointment', 'slot', 'booking', 'schedule', 'calendar', 'book'],
            'document_requirements': ['document', 'form', 'requirement', 'paperwork', 'certificate', 'ds160'],
            'processing_times': ['processing', 'timeline', 'duration', 'wait', 'delay', 'how long'],
            'interview_preparation': ['interview', 'question', 'preparation', 'practice', 'tips'],
            'visa_stamping': ['stamping', 'passport', 'visa', 'stamp', 'collection', 'pickup'],
            'fee_payment': ['fee', 'payment', 'cost', 'charge', 'money', 'dollar', 'pay'],
            'embassy_updates': ['embassy', 'consulate', 'closure', 'holiday', 'announcement'],
            'visa_denial': ['denial', 'rejected', 'refused', '221g', 'administrative'],
            'travel_restrictions': ['travel', 'restriction', 'ban', 'covid', 'entry'],
        }
        
        topic_scores = {}
        for topic, keywords in visa_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            
            if score > 0:
                topic_scores[topic] = score / len(keywords)
        
        if topic_scores:
            best_topic = max(topic_scores.items(), key=lambda x: x[1])
            return best_topic[0], best_topic[1]
        
        return 'general', 0.1
    
    async def step3_topic_modeling(self, session_files: List[Path] = None) -> List[Path]:
        """Step 3: Topic Modeling - NO DATABASE REQUIRED"""
        logger.info("Starting Step 3: Topic Modeling")
        
        if not session_files:
            session_files = list(self.sessions_dir.glob("*.jsonl"))
        
        topic_files = []
        
        for session_file in session_files:
            logger.info(f"Processing topics for: {session_file}")
            
            sessions_with_topics = []
            
            with open(session_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        session_data = json.loads(line)
                        
                        # Combine all messages for topic analysis
                        session_text = " ".join([
                            msg['content'] for msg in session_data['messages'] 
                            if msg['content']
                        ])
                        
                        if session_text.strip():
                            topic, confidence = self.classify_topic_simple(session_text)
                            session_data['topic'] = topic
                            session_data['topic_confidence'] = confidence
                            session_data['has_question'] = '?' in session_text
                        else:
                            session_data['topic'] = 'empty'
                            session_data['topic_confidence'] = 0.0
                            session_data['has_question'] = False
                        
                        sessions_with_topics.append(session_data)
                    
                    except json.JSONDecodeError:
                        continue
            
            # Save file with topics
            topic_filename = session_file.stem + "_topics.jsonl"
            topic_path = self.topics_dir / topic_filename
            
            with open(topic_path, 'w', encoding='utf-8') as f:
                for session in sessions_with_topics:
                    f.write(json.dumps(session, ensure_ascii=False, default=str) + '\n')
            
            topic_files.append(topic_path)
            
            # Log topic summary
            topic_counts = defaultdict(int)
            for session in sessions_with_topics:
                topic_counts[session['topic']] += 1
            
            logger.info(f"Topic distribution: {dict(topic_counts)}")
        
        logger.info(f"Step 3 completed: Created {len(topic_files)} topic-labeled files")
        return topic_files
    
    async def step4_embedding_storage(self, topic_files: List[Path] = None) -> Dict[str, Any]:
        """Step 4: Embedding Storage - OPTIONAL (requires OpenAI API)"""
        logger.info("Starting Step 4: Embedding & Vector Storage")
        
        if not topic_files:
            topic_files = list(self.topics_dir.glob("*.jsonl"))
        
        # Check if OpenAI is available
        try:
            import openai
            openai_client = openai.OpenAI()
        except ImportError:
            logger.warning("OpenAI not installed - skipping embedding generation")
            return {"error": "OpenAI not available", "vectors_created": 0}
        except Exception as e:
            logger.warning(f"OpenAI client error - skipping embeddings: {e}")
            return {"error": str(e), "vectors_created": 0}
        
        all_vectors = []
        
        for topic_file in topic_files:
            logger.info(f"Creating embeddings for: {topic_file}")
            
            with open(topic_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        session_data = json.loads(line)
                        
                        conversation_text = "\n".join([
                            f"{msg.get('username', 'User')}: {msg['content']}"
                            for msg in session_data['messages']
                            if msg['content']
                        ])
                        
                        if not conversation_text.strip():
                            continue
                        
                        # Generate embedding
                        response = await openai_client.embeddings.create(
                            model="text-embedding-ada-002",
                            input=conversation_text
                        )
                        
                        embedding = response.data[0].embedding
                        
                        vector_record = {
                            "id": f"{topic_file.stem}_{session_data['session_id']}",
                            "embedding": embedding,
                            "metadata": {
                                "type": "conversation_session",
                                "session_id": session_data['session_id'],
                                "topic": session_data['topic'],
                                "message_count": session_data['message_count'],
                                "conversation_text": conversation_text[:1000],
                            }
                        }
                        
                        all_vectors.append(vector_record)
                        
                    except Exception as e:
                        logger.error(f"Error creating embedding: {e}")
                        continue
        
        # Save vectors
        vectors_path = self.embeddings_dir / "conversation_vectors.json"
        with open(vectors_path, 'w', encoding='utf-8') as f:
            json.dump(all_vectors, f, indent=2)
        
        summary = {
            "total_vectors": len(all_vectors),
            "processing_date": datetime.utcnow().isoformat(),
            "files_processed": len(topic_files)
        }
        
        summary_path = self.embeddings_dir / "embedding_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Step 4 completed: Created {len(all_vectors)} embeddings")
        return summary
    
    async def export_to_csv(self, output_path: str = None) -> Path:
        """Export all processed data to CSV - NO DATABASE REQUIRED"""
        if not output_path:
            output_path = self.exports_dir / f"conversations_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        output_path = Path(output_path)
        
        all_sessions = []
        
        for topic_file in self.topics_dir.glob("*.jsonl"):
            with open(topic_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        session_data = json.loads(line)
                        
                        for msg in session_data['messages']:
                            csv_row = {
                                'session_id': session_data['session_id'],
                                'session_topic': session_data['topic'],
                                'session_start_time': session_data['start_time'],
                                'message_id': msg['message_id'],
                                'user_id': msg.get('user_id', 'unknown'),
                                'username': msg.get('username', 'anonymous'),
                                'content': msg['content'],
                                'timestamp': msg['timestamp'],
                            }
                            all_sessions.append(csv_row)
                    except json.JSONDecodeError:
                        continue
        
        df = pd.DataFrame(all_sessions)
        df.to_csv(output_path, index=False)
        
        logger.info(f"Exported {len(all_sessions)} conversation records to {output_path}")
        return output_path
    
    async def run_full_pipeline(self, input_csv_files: List[Path] = None) -> Dict[str, Any]:
        """Run complete pipeline on CSV files - NO DATABASE REQUIRED"""
        logger.info("Starting CSV-based processing pipeline (NO DATABASE REQUIRED)")
        
        results = {
            "start_time": datetime.utcnow().isoformat(),
            "steps_completed": []
        }
        
        try:
            # Step 1: Process CSV files
            chunk_files = await self.step1_preprocessing_chunking(input_csv_files)
            results["chunk_files"] = len(chunk_files)
            results["steps_completed"].append("step1_csv_chunking")
            
            if not chunk_files:
                results["error"] = "No CSV files to process"
                return results
            
            # Step 2: Sessionization
            session_files = await self.step2_sessionization(chunk_files)
            results["session_files"] = len(session_files)
            results["steps_completed"].append("step2_sessionization")
            
            # Step 3: Topic modeling
            topic_files = await self.step3_topic_modeling(session_files)
            results["topic_files"] = len(topic_files)
            results["steps_completed"].append("step3_topic_modeling")
            
            # Step 4: Embeddings (optional)
            embedding_summary = await self.step4_embedding_storage(topic_files)
            results["embeddings_created"] = embedding_summary.get("total_vectors", 0)
            results["steps_completed"].append("step4_embeddings")
            
            # Export to CSV
            csv_export = await self.export_to_csv()
            results["csv_export"] = str(csv_export)
            results["steps_completed"].append("csv_export")
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results["error"] = str(e)
        
        results["end_time"] = datetime.utcnow().isoformat()
        
        logger.info(f"CSV pipeline completed: {results}")
        return results

async def main():
    """CLI for CSV-based processing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CSV Data Processing Pipeline - NO DATABASE REQUIRED")
    parser.add_argument("--input-csv", nargs="+", type=Path,
                       help="Input CSV files to process")
    parser.add_argument("--step", choices=["1", "2", "3", "4", "all"],
                       help="Run specific step")
    parser.add_argument("--export-only", action="store_true",
                       help="Only export existing processed data")
    
    args = parser.parse_args()
    
    processor = CSVDataProcessor()
    
    try:
        if args.export_only:
            export_path = await processor.export_to_csv()
            print(f"Exported to: {export_path}")
        elif args.step == "all" or not args.step:
            results = await processor.run_full_pipeline(args.input_csv)
            print(f"Processing completed: {results}")
        elif args.step == "1":
            files = await processor.step1_preprocessing_chunking(args.input_csv)
            print(f"Step 1 completed: {len(files)} chunks created")
        elif args.step == "2":
            files = await processor.step2_sessionization()
            print(f"Step 2 completed: {len(files)} session files")
        elif args.step == "3":
            files = await processor.step3_topic_modeling()
            print(f"Step 3 completed: {len(files)} topic files")
        elif args.step == "4":
            summary = await processor.step4_embedding_storage()
            print(f"Step 4 completed: {summary}")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

