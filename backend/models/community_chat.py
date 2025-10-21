"""
Community Chat System - Real-time group chat for visa community
Powered by MongoDB for scalable conversation history
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from models.mongodb_chat import chat_db

logger = logging.getLogger(__name__)


class ChatDatabase:
    """MongoDB-based chat database wrapper for backward compatibility"""
    
    def __init__(self):
        """Initialize chat database (MongoDB)"""
        if not chat_db:
            logger.warning("⚠️  MongoDB chat database not available - chat features disabled")
            self.db = None
        else:
            self.db = chat_db
            logger.info(f"✅ Chat database initialized (MongoDB)")
    
    def save_message(self, user_email: str, display_name: str, message: str, message_type: str = 'text', metadata: dict = None, reply_to: str = None, room_id: str = 'general'):
        """Save a chat message to MongoDB"""
        if not self.db:
            logger.warning("⚠️  Cannot save message - MongoDB not available")
            return None
        return self.db.save_message(
            user_email=user_email,
            display_name=display_name,
            message=message,
            message_type=message_type,
            room_id=room_id,
            metadata=metadata,
            reply_to=reply_to
        )
    
    def get_recent_messages(self, limit: int = 50, room_id: str = 'general') -> List[Dict]:
        """Get recent chat messages from MongoDB"""
        if not self.db:
            logger.warning("⚠️  Cannot get messages - MongoDB not available")
            return []
        return self.db.get_recent_messages(limit=limit, room_id=room_id)
    
    def edit_message(self, message_id: str, new_content: str, user_email: str, edit_window_minutes: int = 15) -> Dict:
        """Edit a chat message (wrapper for MongoDB method)"""
        if not self.db:
            logger.warning("⚠️  Cannot edit message - MongoDB not available")
            return {'success': False, 'message': 'Database not available'}
        return self.db.edit_message(message_id, new_content, user_email, edit_window_minutes)


class ConnectionManager:
    """Manage WebSocket connections for real-time chat with room isolation"""
    
    def __init__(self):
        # Active connections per room: {room_id: {email: {'ws': websocket, 'display_name': name}}}
        self.rooms: Dict[str, Dict[str, Dict]] = {}
        self.db = ChatDatabase()
    
    def get_display_name(self, email: str, room_id: str) -> str:
        """Get display name for a user in a specific room"""
        if room_id in self.rooms and email in self.rooms[room_id]:
            return self.rooms[room_id][email]['display_name']
        # Fallback to email-based name if not connected
        return email.split('@')[0].capitalize() if '@' in email else email
    
    async def connect(self, websocket: WebSocket, user_email: str, display_name: str, room_id: str = "general"):
        """Accept new connection to a specific room"""
        await websocket.accept()
        
        # Initialize room if it doesn't exist
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        
        self.rooms[room_id][user_email] = {
            'ws': websocket,
            'display_name': display_name
        }
        
        # Send recent message history for this room
        history = self.db.get_recent_messages(limit=50, room_id=room_id)
        await websocket.send_json({
            'type': 'history',
            'messages': history,
            'room_id': room_id
        })
        
        # Notify others in this room about new user
        await self.broadcast_system_message(f"{display_name} joined the chat", room_id=room_id, exclude=user_email)
        await self.broadcast_user_list(room_id)
        
        logger.info(f"✅ {user_email} ({display_name}) connected to room '{room_id}'. Room users: {len(self.rooms[room_id])}")
    
    def disconnect(self, user_email: str, room_id: str):
        """Remove connection from a specific room"""
        if room_id in self.rooms and user_email in self.rooms[room_id]:
            del self.rooms[room_id][user_email]
            # Clean up empty rooms
            if not self.rooms[room_id]:
                del self.rooms[room_id]
            logger.info(f"❌ {user_email} disconnected from room '{room_id}'. Remaining rooms: {len(self.rooms)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific websocket"""
        await websocket.send_text(message)
    
    async def broadcast(self, message: Dict, room_id: str, exclude: str = None):
        """Broadcast message to all connected clients in a specific room"""
        if room_id not in self.rooms:
            return
        
        disconnected = []
        
        for email, conn_info in self.rooms[room_id].items():
            if exclude and email == exclude:
                continue
            
            try:
                await conn_info['ws'].send_json(message)
            except Exception as e:
                logger.error(f"Error sending to {email} in room {room_id}: {e}")
                disconnected.append(email)
        
        # Clean up disconnected clients
        for email in disconnected:
            self.disconnect(email, room_id)
    
    async def broadcast_system_message(self, message: str, room_id: str, exclude: str = None):
        """Broadcast a system message to a specific room"""
        msg_data = {
            'type': 'system',
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.broadcast(msg_data, room_id=room_id, exclude=exclude)
    
    async def broadcast_user_list(self, room_id: str):
        """Broadcast list of online users in a specific room"""
        if room_id not in self.rooms:
            return
        
        users = [
            {
                'email': email,
                'displayName': conn_info['display_name']
            }
            for email, conn_info in self.rooms[room_id].items()
        ]
        msg_data = {
            'type': 'users',
            'users': users,
            'count': len(users)
        }
        await self.broadcast(msg_data, room_id=room_id)
    
    async def update_user_display_name(self, user_email: str, new_display_name: str, room_id: str):
        """Update display name for a connected user in a specific room"""
        if room_id in self.rooms and user_email in self.rooms[room_id]:
            old_name = self.rooms[room_id][user_email]['display_name']
            self.rooms[room_id][user_email]['display_name'] = new_display_name
            logger.info(f"✅ Updated display name for {user_email} in room {room_id}: {old_name} → {new_display_name}")
            
            # Broadcast updated user list to all clients in this room
            await self.broadcast_user_list(room_id)
            
            # Optionally notify others about the name change
            await self.broadcast_system_message(f"{old_name} is now known as {new_display_name}", room_id=room_id)
            return True
        return False
    
    async def handle_message(self, user_email: str, display_name: str, data: Dict, room_id: str = "general"):
        """Handle incoming message from user in a specific room"""
        message_type = data.get('type', 'text')
        
        logger.info(f"📨 Received message from {user_email} in room '{room_id}': type={message_type}, data={data}")
        
        # Handle profile update message
        if message_type == 'profile_update':
            new_display_name = data.get('displayName', '')
            if new_display_name:
                await self.update_user_display_name(user_email, new_display_name, room_id)
            return None
        
        # Regular chat message
        message_content = data.get('message', '')
        reply_to = data.get('replyTo')  # Get reply information
        image_url = data.get('imageUrl')  # Get image URL for image messages
        
        logger.info(f"📝 Message details: content='{message_content}', image_url={image_url}")
        
        # Get current display name from active connections in this room
        current_display_name = self.get_display_name(user_email, room_id)
        
        # Prepare metadata for image messages
        metadata = None
        if message_type == 'image' and image_url:
            metadata = {
                'image_url': image_url,
                'image_filename': data.get('imageFilename'),
                'image_size': data.get('imageSize')
            }
        
        # Save to database with reply information, metadata, and room_id
        saved_msg = self.db.save_message(
            user_email, 
            current_display_name, 
            message_content, 
            message_type,
            metadata=metadata,
            reply_to=reply_to,
            room_id=room_id
        )
        
        # Broadcast to all users in this room
        msg_data = {
            'type': 'message',
            'id': saved_msg['id'],
            'userEmail': user_email,
            'displayName': current_display_name,
            'message': message_content,
            'messageType': message_type,
            'timestamp': saved_msg['timestamp']
        }
        
        # Include image URL for image messages
        if message_type == 'image' and image_url:
            msg_data['imageUrl'] = image_url
            logger.info(f"🖼️ Including imageUrl in broadcast: {image_url}")
        
        # Include reply information in broadcast
        if saved_msg.get('replyTo'):
            msg_data['replyTo'] = saved_msg['replyTo']
        
        logger.info(f"📡 Broadcasting message to room '{room_id}': {msg_data}")
        await self.broadcast(msg_data, room_id=room_id)
        
        return saved_msg


# Global connection manager
chat_manager = ConnectionManager()
