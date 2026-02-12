"""
MongoDB Chat Database
Handles chat messages storage and retrieval with full history
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from bson import ObjectId
from models.mongodb_connection import mongodb_client

logger = logging.getLogger(__name__)


class MongoDBChatDatabase:
    """MongoDB-based chat database with full conversation history"""
    
    def __init__(self):
        """Initialize MongoDB chat database"""
        if mongodb_client is None or mongodb_client.db is None:
            raise Exception("MongoDB connection not available")
        
        self.db = mongodb_client.db
        self.messages = self.db.messages
        # Presence collection for online users across machines
        self.presence = self.db.chat_presence

        # Ensure indexes (idempotent)
        try:
            self.presence.create_index([('room_id', 1), ('email', 1)], unique=True)
            self.presence.create_index([('online', 1)])
            self.presence.create_index([('last_seen', 1)])
        except Exception as e:
            logger.warning(f"⚠️ Could not ensure presence indexes: {e}")
        
        logger.info("✅ MongoDB Chat Database initialized")
    
    def save_message(
        self, 
        user_email: str, 
        display_name: str, 
        message: str, 
        message_type: str = 'text',
        room_id: str = 'general',
        metadata: Optional[Dict] = None,
        reply_to: Optional[str] = None,
        mentioned_users: Optional[List[str]] = None,
        attachments: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Save a chat message to MongoDB
        
        Args:
            user_email: User's email address
            display_name: User's display name
            message: Message content
            message_type: Type of message (text, system, image, file)
            room_id: Room/channel ID (for future multi-room support)
            metadata: Additional metadata (client info, IP, etc.)
            reply_to: ID of message being replied to
        
        Returns:
            Dict: Saved message document
        """
        try:
            # Build message document
            message_doc = {
                'user_email': user_email,
                'display_name': display_name,
                'message': message,
                'message_type': message_type,
                'room_id': room_id,
                'reactions': [],
                'edited': False,
                'edited_at': None,
                'deleted': False,
                'metadata': metadata or {},
                'created_at': datetime.now(timezone.utc),
                'topic_id': None,  # Will be set below
                # Rich content fields
                'mentioned_users': mentioned_users or [],  # List of @mentioned email addresses
                'attachments': attachments or [],  # File attachments
                'reply_count': 0  # Denormalized count of replies to this message
            }
            
            # If replying to a message, store a snapshot (not just ID)
            # This is more efficient and preserves context even if original is edited/deleted
            # Also compute topic_id for thread segregation
            if reply_to:
                try:
                    from bson.objectid import ObjectId
                    replied_msg = self.messages.find_one({'_id': ObjectId(reply_to)})
                    if replied_msg:
                        # Store snapshot of replied message (Telegram/WhatsApp approach)
                        message_doc['reply_to'] = {
                            'id': str(replied_msg['_id']),
                            'user_email': replied_msg['user_email'],
                            'display_name': replied_msg['display_name'],
                            'message': replied_msg['message'][:150],  # Truncate for space efficiency
                            'timestamp': replied_msg['created_at']
                        }
                        # Inherit topic_id from parent (for thread segregation)
                        # If parent has topic_id, use it; otherwise parent is the topic root
                        message_doc['topic_id'] = replied_msg.get('topic_id') or str(replied_msg['_id'])
                    else:
                        logger.warning(f"Replied message {reply_to} not found")
                        # Fallback: use reply_to as topic_id
                        message_doc['topic_id'] = reply_to
                except Exception as e:
                    logger.error(f"Error fetching replied message: {e}")
                    message_doc['topic_id'] = reply_to
            
            result = self.messages.insert_one(message_doc)
            message_doc['_id'] = result.inserted_id
            
            # Invalidate cached history for this room (if enabled)
            try:
                from services.cache import cache
                cache.delete(f"chat:history:{room_id}:50")
            except Exception:
                pass
            
            # If this is a reply, increment the parent's reply_count
            if reply_to:
                try:
                    self.messages.update_one(
                        {'_id': ObjectId(reply_to)},
                        {'$inc': {'reply_count': 1}}
                    )
                except Exception as e:
                    logger.warning(f"Could not increment reply_count: {e}")
            
            # Update user statistics (non-blocking)
            try:
                from models.mongodb_auth import auth_db
                if auth_db:
                    auth_db.increment_user_message_count(user_email)
            except Exception as e:
                logger.warning(f"Could not update user stats: {e}")
            
            # Convert for API response
            return self._format_message(message_doc)
            
        except Exception as e:
            logger.error(f"❌ Error saving message: {e}")
            raise
    
    def get_recent_messages(
        self, 
        limit: int = 50, 
        room_id: str = 'general',
        skip: int = 0
    ) -> List[Dict]:
        """
        Get recent chat messages
        
        Args:
            limit: Number of messages to retrieve
            room_id: Room/channel ID
            skip: Number of messages to skip (for pagination)
        
        Returns:
            List[Dict]: List of message documents
        """
        try:
            # Check cache first (5s TTL set on write path)
            try:
                from services.cache import cache
                cache_key = f"chat:history:{room_id}:{limit}"
                cached = cache.get_json(cache_key)
                if cached:
                    return cached
            except Exception:
                cached = None
            
            cursor = self.messages.find(
                {
                    'room_id': room_id,
                    'deleted': False
                }
            ).sort('created_at', -1).skip(skip).limit(limit)
            
            # Convert to list and reverse (oldest first)
            messages = list(cursor)
            messages.reverse()
            formatted = [self._format_message(msg) for msg in messages]
            
            # Cache briefly to absorb reconnect storms
            try:
                from services.cache import cache
                cache.set_json(cache_key, formatted, ttl_seconds=5)
            except Exception:
                pass
            
            return formatted
            
        except Exception as e:
            logger.error(f"❌ Error getting recent messages: {e}")
            return []
    
    def get_user_messages(
        self, 
        user_email: str, 
        limit: int = 100
    ) -> List[Dict]:
        """Get messages from a specific user"""
        try:
            cursor = self.messages.find(
                {
                    'user_email': user_email,
                    'deleted': False
                }
            ).sort('created_at', -1).limit(limit)
            
            messages = list(cursor)
            messages.reverse()
            
            return [self._format_message(msg) for msg in messages]
            
        except Exception as e:
            logger.error(f"❌ Error getting user messages: {e}")
            return []
    
    def search_messages(
        self, 
        search_query: str, 
        limit: int = 50
    ) -> List[Dict]:
        """
        Search messages by content (requires text index)
        
        Note: Create text index first:
        db.messages.create_index({'message': 'text'})
        """
        try:
            cursor = self.messages.find(
                {
                    '$text': {'$search': search_query},
                    'deleted': False
                }
            ).sort('created_at', -1).limit(limit)
            
            return [self._format_message(msg) for msg in cursor]
            
        except Exception as e:
            logger.warning(f"Text search not available: {e}")
            # Fallback to regex search
            cursor = self.messages.find(
                {
                    'message': {'$regex': search_query, '$options': 'i'},
                    'deleted': False
                }
            ).sort('created_at', -1).limit(limit)
            
            return [self._format_message(msg) for msg in cursor]
    
    def edit_message(
        self, 
        message_id: str, 
        new_content: str, 
        user_email: str,
        edit_window_minutes: int = 15
    ) -> Dict[str, Any]:
        """
        Edit a message (only by original author within time window)
        
        Args:
            message_id: Message ID to edit
            new_content: New message content
            user_email: Email of user attempting to edit
            edit_window_minutes: Time window in minutes to allow editing (default 15)
        
        Returns:
            Dict: {'success': bool, 'message': str, 'edited_message': dict}
        """
        try:
            # First, check if the message exists and if user is authorized
            message = self.messages.find_one({
                '_id': ObjectId(message_id),
                'user_email': user_email,
                'deleted': False
            })
            
            if not message:
                return {'success': False, 'message': 'Message not found or not authorized'}
            
            # Check if within edit window (15 minutes by default)
            message_time = message['created_at']
            # Ensure message_time is timezone-aware
            if message_time.tzinfo is None:
                message_time = message_time.replace(tzinfo=timezone.utc)
            current_time = datetime.now(timezone.utc)
            time_diff = current_time - message_time
            
            if time_diff.total_seconds() > (edit_window_minutes * 60):
                minutes_ago = int(time_diff.total_seconds() / 60)
                return {
                    'success': False, 
                    'message': f'Edit window expired. Message was posted {minutes_ago} minutes ago. Can only edit within {edit_window_minutes} minutes.'
                }
            
            # Update the message
            result = self.messages.update_one(
                {'_id': ObjectId(message_id)},
                {
                    '$set': {
                        'message': new_content,
                        'edited': True,
                        'edited_at': datetime.now(timezone.utc)
                    }
                }
            )
            
            if result.modified_count > 0:
                # Get the updated message
                updated_message = self.messages.find_one({'_id': ObjectId(message_id)})
                logger.info(f"✅ Message {message_id} edited by {user_email}")
                return {
                    'success': True,
                    'message': 'Message edited successfully',
                    'edited_message': self._format_message(updated_message)
                }
            
            return {'success': False, 'message': 'Failed to update message'}
            
        except Exception as e:
            logger.error(f"❌ Error editing message: {e}")
            return {'success': False, 'message': str(e)}
    
    def delete_message(
        self, 
        message_id: str, 
        user_email: str,
        hard_delete: bool = False
    ) -> bool:
        """
        Delete a message (soft delete by default)
        
        Args:
            message_id: Message ID to delete
            user_email: Email of user attempting to delete
            hard_delete: If True, permanently remove from database
        
        Returns:
            bool: True if deleted successfully
        """
        try:
            if hard_delete:
                # Permanent deletion
                result = self.messages.delete_one(
                    {
                        '_id': ObjectId(message_id),
                        'user_email': user_email
                    }
                )
                success = result.deleted_count > 0
            else:
                # Soft delete (mark as deleted)
                result = self.messages.update_one(
                    {
                        '_id': ObjectId(message_id),
                        'user_email': user_email,
                        'deleted': False
                    },
                    {
                        '$set': {
                            'deleted': True,
                            'message': '[deleted]'
                        }
                    }
                )
                success = result.modified_count > 0
            
            if success:
                logger.info(f"✅ Message {message_id} deleted by {user_email}")
            else:
                logger.warning(f"⚠️ Message {message_id} not found or not authorized")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error deleting message: {e}")
            return False
    
    def add_reaction(
        self, 
        message_id: str, 
        user_email: str, 
        emoji: str
    ) -> bool:
        """Add emoji reaction to a message"""
        try:
            result = self.messages.update_one(
                {'_id': ObjectId(message_id)},
                {
                    '$addToSet': {
                        'reactions': {
                            'emoji': emoji,
                            'user_email': user_email,
                            'created_at': datetime.now(timezone.utc)
                        }
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error adding reaction: {e}")
            return False
    
    def get_message_count(self, room_id: str = 'general') -> int:
        """Get total message count for a room"""
        try:
            return self.messages.count_documents({
                'room_id': room_id,
                'deleted': False
            })
        except Exception as e:
            logger.error(f"❌ Error counting messages: {e}")
            return 0
    
    def get_stats(self) -> Dict:
        """Get chat statistics"""
        try:
            total_messages = self.messages.count_documents({'deleted': False})
            total_users = len(self.messages.distinct('user_email'))
            
            # Get messages from last 24 hours
            from datetime import timedelta
            last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_messages = self.messages.count_documents({
                'created_at': {'$gte': last_24h},
                'deleted': False
            })
            
            return {
                'total_messages': total_messages,
                'total_users': total_users,
                'messages_last_24h': recent_messages
            }
        except Exception as e:
            logger.error(f"❌ Error getting stats: {e}")
            return {}
    
    def delete_old_messages(self, days_old: int = 30, room_id: Optional[str] = None) -> Dict[str, int]:
        """
        Delete messages older than specified days (admin function)
        
        Args:
            days_old: Delete messages older than this many days
            room_id: Optional room filter. If None, deletes from all rooms
        
        Returns:
            Dict with deleted count
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            query = {'created_at': {'$lt': cutoff_date}}
            if room_id:
                query['room_id'] = room_id
            
            result = self.messages.delete_many(query)
            deleted_count = result.deleted_count
            
            logger.info(f"✅ Deleted {deleted_count} messages older than {days_old} days" + 
                       (f" from room {room_id}" if room_id else " from all rooms"))
            
            return {
                'deleted': deleted_count,
                'days_old': days_old,
                'room_id': room_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error deleting old messages: {e}")
            return {'deleted': 0, 'error': str(e)}
    
    def delete_room_messages(self, room_id: str, keep_last_n: int = 0) -> Dict[str, int]:
        """
        Delete all messages from a specific room (admin function)
        
        Args:
            room_id: Room ID to clear
            keep_last_n: Keep the last N messages (0 = delete all)
        
        Returns:
            Dict with deleted count
        """
        try:
            if keep_last_n > 0:
                # Get IDs of messages to keep
                messages_to_keep = self.messages.find(
                    {'room_id': room_id}
                ).sort('created_at', -1).limit(keep_last_n)
                keep_ids = [msg['_id'] for msg in messages_to_keep]
                
                # Delete all except those to keep
                result = self.messages.delete_many({
                    'room_id': room_id,
                    '_id': {'$nin': keep_ids}
                })
            else:
                # Delete all messages in room
                result = self.messages.delete_many({'room_id': room_id})
            
            deleted_count = result.deleted_count
            logger.info(f"✅ Deleted {deleted_count} messages from room {room_id}")
            
            return {
                'deleted': deleted_count,
                'room_id': room_id,
                'kept': keep_last_n
            }
            
        except Exception as e:
            logger.error(f"❌ Error deleting room messages: {e}")
            return {'deleted': 0, 'error': str(e)}
    
    def update_presence(self, room_id: str, email: str, display_name: str, online: bool = True) -> None:
        """Upsert user's presence record for a room"""
        try:
            now = datetime.now(timezone.utc)
            self.presence.update_one(
                {'room_id': room_id, 'email': email.lower().strip()},
                {
                    '$set': {
                        'display_name': display_name,
                        'online': online,
                        'last_seen': now
                    },
                    '$setOnInsert': {
                        'first_seen': now
                    }
                },
                upsert=True
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to update presence for {email} in {room_id}: {e}")
    
    def get_online_count(self, room_id: str) -> int:
        """Get online user count for a room from presence collection"""
        try:
            return self.presence.count_documents({'room_id': room_id, 'online': True})
        except Exception:
            return 0
    
    def get_presence_counts_map(self) -> Dict[str, int]:
        """Get online counts per room using aggregation"""
        try:
            pipeline = [
                {'$match': {'online': True}},
                {'$group': {'_id': '$room_id', 'count': {'$sum': 1}}},
                {'$project': {'room_id': '$_id', 'count': 1, '_id': 0}}
            ]
            results = list(self.presence.aggregate(pipeline))
            return {r['room_id']: r['count'] for r in results}
        except Exception:
            return {}
    
    def get_room_stats(self) -> List[Dict]:
        """
        Get statistics for all rooms (admin function)
        
        Returns:
            List of room statistics
        """
        try:
            pipeline = [
                {'$match': {'deleted': False}},
                {'$group': {
                    '_id': '$room_id',
                    'message_count': {'$sum': 1},
                    'unique_users': {'$addToSet': '$user_email'},
                    'oldest_message': {'$min': '$created_at'},
                    'newest_message': {'$max': '$created_at'}
                }},
                {'$project': {
                    'room_id': '$_id',
                    'message_count': 1,
                    'user_count': {'$size': '$unique_users'},
                    'oldest_message': 1,
                    'newest_message': 1,
                    '_id': 0
                }}
            ]
            
            results = list(self.messages.aggregate(pipeline))
            return results
            
        except Exception as e:
            logger.error(f"❌ Error getting room stats: {e}")
            return []
    
    def _format_message(self, message_doc: Dict) -> Dict:
        """Format message document for API response"""
        formatted = {
            'id': str(message_doc['_id']),
            'userEmail': message_doc['user_email'],
            'displayName': message_doc['display_name'],
            'message': message_doc['message'],
            'timestamp': message_doc['created_at'].isoformat(),
            'messageType': message_doc.get('message_type', 'text'),
            'type': message_doc.get('message_type', 'text'),  # Keep for backwards compatibility
            'roomId': message_doc.get('room_id', 'general'),
            'edited': message_doc.get('edited', False),
            'reactions': message_doc.get('reactions', []),
            'topicId': message_doc.get('topic_id'),  # Include topic_id for thread segregation
            'mentionedUsers': message_doc.get('mentioned_users', []),
            'attachments': message_doc.get('attachments', []),
            'replyCount': message_doc.get('reply_count', 0)
        }
        
        # Include image metadata for image messages
        metadata = message_doc.get('metadata')
        if metadata and isinstance(metadata, dict):
            if 'image_url' in metadata:
                formatted['imageUrl'] = metadata['image_url']
        
        # Include reply snapshot if present (already embedded in document)
        reply_to = message_doc.get('reply_to')
        if reply_to and isinstance(reply_to, dict):
            # Convert timestamp if it's a datetime object
            reply_timestamp = reply_to.get('timestamp')
            if hasattr(reply_timestamp, 'isoformat'):
                reply_timestamp = reply_timestamp.isoformat()
            
            formatted['replyTo'] = {
                'id': reply_to['id'],
                'userEmail': reply_to['user_email'],
                'displayName': reply_to['display_name'],
                'message': reply_to['message'],
                'timestamp': reply_timestamp
            }
        
        return formatted


# Global chat database instance
try:
    chat_db = MongoDBChatDatabase()
except Exception as e:
    logger.error(f"Failed to initialize MongoDB chat database: {e}")
    chat_db = None
