"""
Chat Routes
Handles community chat, WebSocket connections, and image uploads
"""

import logging
import uuid
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile, Form

from api.schemas import EditMessageRequest
from models.community_chat import chat_manager
from models.user_auth import auth_db_instance as auth_db
from services.news import compress_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Media directory for uploaded images
MEDIA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "media" / "chat_images"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/history")
async def get_chat_history(limit: int = 50, room_id: str = "general"):
    """Get recent chat history for a specific room"""
    try:
        messages = chat_manager.db.get_recent_messages(limit=limit, room_id=room_id)
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.post("/edit-message")
async def edit_chat_message(request: EditMessageRequest):
    """Edit a chat message (within 15 minute window)"""
    try:
        result = chat_manager.db.edit_message(
            request.message_id,
            request.new_content,
            request.user_email
        )
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=400, detail=result['message'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to edit message: {str(e)}")


@router.get("/users")
async def get_online_users(room_id: str = "general"):
    """Get list of currently online users in a specific room"""
    if room_id in chat_manager.rooms:
        users = list(chat_manager.rooms[room_id].keys())
        return {"users": users, "count": len(users), "room_id": room_id}
    return {"users": [], "count": 0, "room_id": room_id}


@router.get("/room-stats")
async def get_room_statistics():
    """Get statistics for all chat rooms (online users and message counts)"""
    try:
        stats = chat_manager.get_room_statistics()
        return {
            "success": True,
            "rooms": stats,
            "total_rooms": len(stats),
            "total_online_users": sum(room['online_users'] for room in stats)
        }
    except Exception as e:
        logger.error(f"❌ Error getting room statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get room statistics: {str(e)}")


@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    session_token: str = Form(...)
):
    """
    Upload and compress chat image (AGGRESSIVE compression for cost savings)
    - Max upload: 10MB
    - Auto-resize to 600px max (optimized for chat)
    - Compress to 40% quality (5-20KB target file size)
    - Store in data/media/chat_images/
    """
    try:
        # Verify session
        user = auth_db.get_user_by_session(session_token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file
        file_data = await file.read()
        file_size_mb = len(file_data) / (1024 * 1024)
        
        # Check size limit (10MB)
        if file_size_mb > 10:
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
        
        logger.info(f"📤 Uploading image: {file.filename} ({file_size_mb:.2f}MB) from {user['email']}")
        
        # Compress image
        compressed_data = compress_image(file_data)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}.jpg"
        
        # Save to disk
        file_path = MEDIA_DIR / filename
        with open(file_path, 'wb') as f:
            f.write(compressed_data)
        
        # Return URL
        image_url = f"/media/chat_images/{filename}"
        
        logger.info(f"✅ Image saved: {image_url}")
        
        return {
            "success": True,
            "url": image_url,
            "filename": filename,
            "size": len(compressed_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# WebSocket endpoint (registered separately in main.py due to different decorator)
async def websocket_chat_handler(websocket: WebSocket):
    """WebSocket endpoint for real-time community chat with authentication"""
    # MUST accept connection FIRST before doing anything
    await websocket.accept()
    
    # Get parameters from query string
    query_params = dict(websocket.query_params)
    user_email = query_params.get("user_email", "")
    display_name = query_params.get("display_name", "")
    room_id = query_params.get("room_id", "general")
    session_token = query_params.get("token", "")  # Get authentication token
    
    logger.info(f"🔌 WebSocket connection attempt: email={user_email}, room={room_id}")
    
    # Validate required parameters
    if not user_email or not display_name:
        logger.error("❌ Missing user_email or display_name")
        await websocket.close(code=1008, reason="Missing required parameters")
        return
    
    # Authenticate user with session token
    if not session_token:
        logger.error(f"❌ No authentication token provided for {user_email}")
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    try:
        # Verify session token
        user = auth_db.get_user_by_session(session_token)
        if not user or user['email'].lower() != user_email.lower():
            logger.error(f"❌ Invalid or expired session for {user_email}")
            await websocket.close(code=1008, reason="Invalid or expired session")
            return
        
        # Check if user is banned
        if auth_db.is_user_banned(user_email):
            logger.error(f"❌ Banned user attempted to connect: {user_email}")
            await websocket.close(code=1008, reason="User is banned")
            return
        
        logger.info(f"✅ WebSocket authenticated: {user_email}")
        
    except Exception as e:
        logger.error(f"❌ WebSocket authentication failed: {e}")
        await websocket.close(code=1011, reason="Authentication error")
        return
    
    try:
        # Register with chat manager
        if room_id not in chat_manager.rooms:
            chat_manager.rooms[room_id] = {}
        
        chat_manager.rooms[room_id][user_email] = {
            'ws': websocket,
            'display_name': display_name
        }
        
        # Send history
        history = chat_manager.db.get_recent_messages(limit=50, room_id=room_id)
        await websocket.send_json({
            'type': 'history',
            'messages': history,
            'room_id': room_id
        })
        
        # Notify others (incremental update for performance)
        await chat_manager.broadcast_system_message(f"{display_name} joined the chat", room_id=room_id, exclude=user_email)
        await chat_manager.broadcast_user_joined(user_email, display_name, room_id, exclude=user_email)
        
        logger.info(f"✅ {user_email} ({display_name}) connected to room '{room_id}'. Room users: {len(chat_manager.rooms[room_id])}")
        
    except Exception as e:
        logger.error(f"❌ WebSocket setup failed: {e}")
        await websocket.close(code=1011, reason=str(e))
        return
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle the message with actual display name and room_id
            await chat_manager.handle_message(user_email, display_name, data, room_id)
            
    except WebSocketDisconnect:
        display_name = chat_manager.disconnect(user_email, room_id)
        if display_name:
            await chat_manager.broadcast_system_message(f"{display_name} left the chat", room_id=room_id)
            await chat_manager.broadcast_user_left(user_email, display_name, room_id)
    except Exception as e:
        logger.error(f"WebSocket error for {user_email} in room {room_id}: {e}")
        chat_manager.disconnect(user_email, room_id)
