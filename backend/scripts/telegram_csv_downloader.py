"""
Telegram CSV Downloader - NO DATABASE REQUIRED
Downloads Telegram conversations directly to CSV files without needing PostgreSQL
"""

import asyncio
import logging
import os
import json
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiofiles
from dataclasses import dataclass

from telethon import TelegramClient, events
from telethon.errors import RPCError, FloodWaitError
from telethon.tl.types import (
    Channel, Chat, User as TelegramUser, 
    MessageService, MessageEmpty
)

from telegram_read import load_config, is_bot_token, ensure_session_path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CSVDownloadConfig:
    """Configuration for CSV download operations."""
    max_messages_per_chat: Optional[int] = None  # None means download all
    start_date: Optional[datetime] = None  # Start from this date
    end_date: Optional[datetime] = None    # End at this date
    batch_size: int = 1000  # Messages to process in each batch
    delay_between_batches: float = 1.0  # Seconds to wait between batches
    output_format: str = "csv"  # "csv" or "jsonl"

class TelegramCSVDownloader:
    """Download Telegram conversations directly to CSV - NO DATABASE REQUIRED."""
    
    def __init__(self, config: CSVDownloadConfig = None):
        self.config = config or CSVDownloadConfig()
        self.client = None
        
        # Set up directories
        self.data_dir = Path("data")
        self.raw_data_dir = self.data_dir / "conversations" / "raw"
        self.logs_dir = self.data_dir / "logs"
        
        for dir_path in [self.raw_data_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def initialize_client(self):
        """Initialize and authenticate the Telegram client - NO DATABASE NEEDED."""
        config = load_config()
        
        api_id = int(config["api_id"])
        api_hash = config["api_hash"]
        phone_or_token = config["phone_or_token"]
        twofa_password = config["twofa_password"]
        session_path = ensure_session_path(config["session_name"])
        
        if not api_id or not api_hash:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required")
        
        self.client = TelegramClient(session_path, api_id, api_hash)
        
        # Start client
        if is_bot_token(phone_or_token):
            await self.client.start(bot_token=phone_or_token)
            logger.info("Authenticated as bot")
        else:
            await self.client.start(phone=phone_or_token, password=twofa_password)
            logger.info("Authenticated as user")
    
    async def discover_available_chats(self) -> List[Dict[str, Any]]:
        """Discover all available chats, groups, and channels."""
        logger.info("Discovering available chats...")
        
        discovered_chats = []
        
        try:
            async for dialog in self.client.iter_dialogs():
                entity = dialog.entity
                
                chat_info = {
                    'id': entity.id,
                    'title': getattr(entity, 'title', None),
                    'username': getattr(entity, 'username', None),
                    'type': self._get_entity_type(entity),
                    'participant_count': getattr(entity, 'participants_count', None),
                    'unread_count': dialog.unread_count,
                    'last_message_date': dialog.date.isoformat() if dialog.date else None,
                }
                
                discovered_chats.append(chat_info)
        
        except Exception as e:
            logger.error(f"Error discovering chats: {e}")
        
        logger.info(f"Discovered {len(discovered_chats)} chats")
        return discovered_chats
    
    def _get_entity_type(self, entity) -> str:
        """Determine the type of Telegram entity."""
        if isinstance(entity, TelegramUser):
            return 'private'
        elif isinstance(entity, Channel):
            if getattr(entity, 'broadcast', False):
                return 'channel'
            else:
                return 'supergroup'
        elif isinstance(entity, Chat):
            return 'group'
        else:
            return 'unknown'
    
    async def download_chat_to_csv(self, chat_info: Dict[str, Any]) -> Dict[str, Any]:
        """Download chat history directly to CSV file - NO DATABASE NEEDED."""
        chat_id = chat_info['id']
        chat_title = chat_info.get('title', f"Chat_{chat_id}")
        
        logger.info(f"Starting CSV download for: {chat_title} (ID: {chat_id})")
        
        download_stats = {
            'chat_id': chat_id,
            'chat_title': chat_title,
            'messages_downloaded': 0,
            'start_time': datetime.utcnow(),
            'status': 'in_progress'
        }
        
        try:
            entity = await self.client.get_entity(chat_id)
            
            # Create safe filename
            safe_title = "".join(c for c in chat_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if self.config.output_format == "csv":
                filename = f"{safe_title}_{chat_id}_{timestamp}.csv"
                file_path = self.raw_data_dir / filename
                
                # Open CSV file for writing
                csv_file = open(file_path, 'w', newline='', encoding='utf-8')
                csv_writer = csv.writer(csv_file)
                
                # Write CSV header
                csv_writer.writerow([
                    'message_id', 'chat_id', 'chat_title', 'user_id', 'username', 
                    'first_name', 'last_name', 'content', 'timestamp', 'message_type',
                    'has_media', 'reply_to_id', 'forward_from', 'edit_date', 'views'
                ])
            
            else:  # JSONL format
                filename = f"{safe_title}_{chat_id}_{timestamp}.jsonl"
                file_path = self.raw_data_dir / filename
                csv_file = open(file_path, 'w', encoding='utf-8')
            
            # Configure message iteration
            iter_kwargs = {
                'limit': self.config.max_messages_per_chat,
                'reverse': False,  # Start from newest
            }
            
            if self.config.start_date:
                iter_kwargs['offset_date'] = self.config.start_date
            
            batch_count = 0
            
            # Download messages
            async for message in self.client.iter_messages(entity, **iter_kwargs):
                try:
                    # Skip if message is outside date range
                    if self.config.end_date and message.date > self.config.end_date:
                        continue
                    if self.config.start_date and message.date < self.config.start_date:
                        break
                    
                    # Skip empty or service messages
                    if isinstance(message, (MessageEmpty, MessageService)):
                        continue
                    
                    # Extract message data
                    message_data = await self._extract_message_data(message, entity)
                    
                    # Write to file
                    if self.config.output_format == "csv":
                        csv_writer.writerow([
                            message_data['message_id'],
                            message_data['chat_id'],
                            message_data['chat_title'],
                            message_data['user_id'],
                            message_data['username'],
                            message_data['first_name'],
                            message_data['last_name'],
                            message_data['content'],
                            message_data['timestamp'],
                            message_data['message_type'],
                            message_data['has_media'],
                            message_data['reply_to_id'],
                            message_data['forward_from'],
                            message_data['edit_date'],
                            message_data['views']
                        ])
                    else:  # JSONL
                        csv_file.write(json.dumps(message_data, default=str, ensure_ascii=False) + '\n')
                    
                    download_stats['messages_downloaded'] += 1
                    
                    # Batch processing with delay
                    if download_stats['messages_downloaded'] % self.config.batch_size == 0:
                        batch_count += 1
                        logger.info(f"Downloaded {download_stats['messages_downloaded']} messages")
                        
                        if self.config.delay_between_batches > 0:
                            await asyncio.sleep(self.config.delay_between_batches)
                
                except FloodWaitError as e:
                    logger.warning(f"Rate limited, waiting {e.seconds} seconds")
                    await asyncio.sleep(e.seconds)
                    continue
                
                except Exception as e:
                    logger.error(f"Error processing message {getattr(message, 'id', 'unknown')}: {e}")
                    continue
            
            # Close file
            csv_file.close()
            
            download_stats['status'] = 'completed'
            download_stats['end_time'] = datetime.utcnow()
            download_stats['file_path'] = str(file_path)
            download_stats['duration_seconds'] = (download_stats['end_time'] - download_stats['start_time']).total_seconds()
            
            logger.info(f"Completed {chat_title}: {download_stats['messages_downloaded']} messages → {file_path}")
        
        except Exception as e:
            download_stats['status'] = 'error'
            download_stats['error'] = str(e)
            logger.error(f"Failed to download {chat_title}: {e}")
            
            # Close file if it was opened
            try:
                csv_file.close()
            except:
                pass
        
        return download_stats
    
    async def _extract_message_data(self, message, entity) -> Dict[str, Any]:
        """Extract message data for CSV export."""
        # Get sender information
        sender_id = None
        username = None
        first_name = None
        last_name = None
        
        if message.sender:
            sender_id = message.sender.id
            username = getattr(message.sender, 'username', None)
            first_name = getattr(message.sender, 'first_name', None)
            last_name = getattr(message.sender, 'last_name', None)
        
        # Extract content
        content = message.message or ""
        
        # Handle replies
        reply_to_id = None
        if hasattr(message, 'reply_to') and message.reply_to:
            reply_to_id = message.reply_to.reply_to_msg_id
        
        # Handle forwards
        forward_from = None
        if message.forward:
            if hasattr(message.forward, 'from_name'):
                forward_from = message.forward.from_name
            elif hasattr(message.forward, 'from_id'):
                forward_from = str(message.forward.from_id)
        
        return {
            'message_id': message.id,
            'chat_id': entity.id,
            'chat_title': getattr(entity, 'title', None),
            'user_id': sender_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'content': content,
            'timestamp': message.date.isoformat(),
            'message_type': 'media' if message.media else 'text',
            'has_media': bool(message.media),
            'reply_to_id': reply_to_id,
            'forward_from': forward_from,
            'edit_date': message.edit_date.isoformat() if message.edit_date else None,
            'views': getattr(message, 'views', None)
        }
    
    async def download_all_to_csv(self, chat_filter: Optional[List[int]] = None) -> Dict[str, Any]:
        """Download all available chats to CSV files - NO DATABASE NEEDED."""
        session_start = datetime.utcnow()
        logger.info("Starting bulk CSV download - NO DATABASE REQUIRED")
        
        # Discover chats
        available_chats = await self.discover_available_chats()
        
        # Filter if requested
        if chat_filter:
            available_chats = [chat for chat in available_chats if chat['id'] in chat_filter]
        
        logger.info(f"Will download {len(available_chats)} chats to CSV")
        
        # Download each chat
        download_results = []
        total_messages = 0
        
        for i, chat_info in enumerate(available_chats, 1):
            logger.info(f"Processing chat {i}/{len(available_chats)}: {chat_info.get('title', chat_info['id'])}")
            
            try:
                result = await self.download_chat_to_csv(chat_info)
                download_results.append(result)
                total_messages += result.get('messages_downloaded', 0)
                
            except Exception as e:
                logger.error(f"Failed to download chat {chat_info.get('title', chat_info['id'])}: {e}")
                download_results.append({
                    'chat_id': chat_info['id'],
                    'status': 'error',
                    'error': str(e)
                })
        
        # Summary
        session_summary = {
            'session_start': session_start.isoformat(),
            'session_end': datetime.utcnow().isoformat(),
            'chats_processed': len(available_chats),
            'total_messages_downloaded': total_messages,
            'successful_downloads': len([r for r in download_results if r.get('status') == 'completed']),
            'failed_downloads': len([r for r in download_results if r.get('status') == 'error']),
            'download_results': download_results,
            'output_directory': str(self.raw_data_dir)
        }
        
        # Save session summary
        summary_file = self.logs_dir / f"csv_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(session_summary, f, indent=2, default=str)
        
        logger.info(f"CSV download completed: {total_messages} messages from {len(available_chats)} chats")
        return session_summary
    
    async def close(self):
        """Close the client connection."""
        if self.client:
            await self.client.disconnect()

# CLI Interface
async def main():
    """Main CLI interface for CSV downloader."""
    import argparse
    from dateutil import parser as date_parser
    
    parser = argparse.ArgumentParser(description="Telegram CSV Downloader - NO DATABASE REQUIRED")
    parser.add_argument("--all", action="store_true",
                       help="Download all available chats to CSV")
    parser.add_argument("--chat-ids", nargs="+", type=int,
                       help="Specific chat IDs to download")
    parser.add_argument("--discover-only", action="store_true",
                       help="Only discover and list available chats")
    parser.add_argument("--max-messages", type=int,
                       help="Maximum messages per chat")
    parser.add_argument("--start-date", type=str,
                       help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str,
                       help="End date (YYYY-MM-DD)")
    parser.add_argument("--format", choices=["csv", "jsonl"], default="csv",
                       help="Output format")
    parser.add_argument("--batch-size", type=int, default=1000,
                       help="Messages per batch")
    parser.add_argument("--delay", type=float, default=1.0,
                       help="Delay between batches (seconds)")
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = None
    end_date = None
    
    if args.start_date:
        start_date = date_parser.parse(args.start_date)
    if args.end_date:
        end_date = date_parser.parse(args.end_date)
    
    # Create config
    config = CSVDownloadConfig(
        max_messages_per_chat=args.max_messages,
        start_date=start_date,
        end_date=end_date,
        batch_size=args.batch_size,
        delay_between_batches=args.delay,
        output_format=args.format
    )
    
    downloader = TelegramCSVDownloader(config)
    
    try:
        await downloader.initialize_client()
        
        if args.discover_only:
            # List available chats
            chats = await downloader.discover_available_chats()
            print(f"\n📋 Discovered {len(chats)} chats:")
            print("-" * 60)
            for chat in chats[:20]:  # Show first 20
                title = chat.get('title', 'No title')
                chat_type = chat.get('type', 'unknown')
                participants = chat.get('participant_count', 'N/A')
                participants_str = f"{participants} members" if participants != 'N/A' else 'N/A'
                print(f"{chat['id']:<12} | {title:<30} | {chat_type:<10} | {participants_str}")
            
            if len(chats) > 20:
                print(f"... and {len(chats) - 20} more chats")
        
        elif args.all:
            # Download all chats
            summary = await downloader.download_all_to_csv(chat_filter=args.chat_ids)
            print(f"\n✅ Download Summary:")
            print(f"📊 Total messages: {summary['total_messages_downloaded']}")
            print(f"📁 Chats processed: {summary['chats_processed']}")
            print(f"✅ Successful: {summary['successful_downloads']}")
            print(f"❌ Failed: {summary['failed_downloads']}")
            print(f"📂 Files saved to: {summary['output_directory']}")
        
        elif args.chat_ids:
            # Download specific chats
            chats = await downloader.discover_available_chats()
            target_chats = [chat for chat in chats if chat['id'] in args.chat_ids]
            
            for chat_info in target_chats:
                result = await downloader.download_chat_to_csv(chat_info)
                print(f"Downloaded {chat_info.get('title', chat_info['id'])}: {result.get('messages_downloaded', 0)} messages")
        
        else:
            print("Use --discover-only to see available chats, --all to download everything, or --chat-ids to download specific chats")
            print("\nExamples:")
            print("  python telegram_csv_downloader.py --discover-only")
            print("  python telegram_csv_downloader.py --all")
            print("  python telegram_csv_downloader.py --chat-ids 123456 789012")
    
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise
    finally:
        await downloader.close()

if __name__ == "__main__":
    asyncio.run(main())
