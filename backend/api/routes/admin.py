"""
Admin API Routes
Administrative endpoints for managing chat messages and system data
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from models.mongodb_chat import chat_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class DeleteOldMessagesRequest(BaseModel):
    """Request model for deleting old messages"""
    days_old: int = 30
    room_id: Optional[str] = None


class DeleteRoomMessagesRequest(BaseModel):
    """Request model for deleting room messages"""
    room_id: str
    keep_last_n: int = 0


@router.get("/chat/stats")
async def get_chat_stats():
    """
    Get chat statistics across all rooms
    
    Returns room-wise message counts, user counts, and date ranges
    """
    try:
        if not chat_db:
            raise HTTPException(status_code=503, detail="Chat database not available")
        
        # Get overall stats
        overall_stats = chat_db.get_stats()
        
        # Get per-room stats
        room_stats = chat_db.get_room_stats()
        
        return {
            "success": True,
            "overall": overall_stats,
            "rooms": room_stats,
            "timestamp": logging.Formatter().formatTime(logging.LogRecord("", 0, "", 0, "", (), None))
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting chat stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/chat/delete-old")
async def delete_old_messages(request: DeleteOldMessagesRequest):
    """
    Delete messages older than specified days
    
    Args:
        days_old: Delete messages older than this many days (default: 30)
        room_id: Optional room filter. If provided, only deletes from that room
    
    Returns:
        Dictionary with deletion count and details
    """
    try:
        if not chat_db:
            raise HTTPException(status_code=503, detail="Chat database not available")
        
        result = chat_db.delete_old_messages(
            days_old=request.days_old,
            room_id=request.room_id
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        logger.info(f"✅ Admin deleted {result['deleted']} old messages")
        
        return {
            "success": True,
            "message": f"Successfully deleted {result['deleted']} messages older than {request.days_old} days",
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting old messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete messages: {str(e)}")


@router.post("/chat/delete-room")
async def delete_room_messages(request: DeleteRoomMessagesRequest):
    """
    Delete all messages from a specific room
    
    Args:
        room_id: Room ID to clear
        keep_last_n: Keep the last N messages (0 = delete all)
    
    Returns:
        Dictionary with deletion count and details
    """
    try:
        if not chat_db:
            raise HTTPException(status_code=503, detail="Chat database not available")
        
        result = chat_db.delete_room_messages(
            room_id=request.room_id,
            keep_last_n=request.keep_last_n
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        logger.info(f"✅ Admin deleted {result['deleted']} messages from room {request.room_id}")
        
        return {
            "success": True,
            "message": f"Successfully deleted {result['deleted']} messages from room {request.room_id}",
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting room messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete room messages: {str(e)}")


@router.get("/chat/room/{room_id}/count")
async def get_room_message_count(room_id: str):
    """
    Get message count for a specific room
    
    Args:
        room_id: Room ID to check
    
    Returns:
        Message count for the room
    """
    try:
        if not chat_db:
            raise HTTPException(status_code=503, detail="Chat database not available")
        
        count = chat_db.get_message_count(room_id=room_id)
        
        return {
            "success": True,
            "room_id": room_id,
            "message_count": count
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting room message count: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get message count: {str(e)}")
