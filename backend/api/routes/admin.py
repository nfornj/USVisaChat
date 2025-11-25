"""
Admin API Routes
Administrative endpoints for managing chat messages and system data
"""

import logging
from fastapi import APIRouter, HTTPException, Query, Header
from typing import Optional
from pydantic import BaseModel

from models.mongodb_chat import chat_db
from models.metrics import metrics_model
from models.news import news_model
from models.mongodb_auth import auth_db
from api.routes import news as news_routes
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"]) 

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "nfornj@gmail.com").lower()

def _require_admin(admin_email: str) -> None:
    email = (admin_email or "").lower().strip()
    if not email:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    if email == ADMIN_EMAIL:
        return
    try:
        user = auth_db.get_user_by_email(email) if auth_db else None
        if user and (user.get("role") == "admin" or user.get("email", "").lower() == ADMIN_EMAIL):
            return
    except Exception:
        pass
    raise HTTPException(status_code=403, detail="Admin privileges required")


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


@router.post("/news/force-refresh")
async def force_refresh_news(email: Optional[str] = Query(None), x_admin_email: Optional[str] = Header(None, convert_underscores=False)):
    """Force refresh AI news (admin only)"""
    _require_admin((email or x_admin_email or ""))
    logger.info(f"🛠️ Admin force-refresh invoked. Module={news_routes} Service before={news_routes.news_service}")
    if not news_routes.news_service:
        news_routes.init_news_service()
        logger.info(f"🛠️ News service initialized. Service after={news_routes.news_service}")
    if not news_routes.news_service:
        raise HTTPException(status_code=500, detail="News service not initialized")

    # Clear existing cached articles to drop any lingering YouTube entries
    try:
        if news_model:
            news_model.clear_all()
            logger.info("🧹 Cleared existing news articles before refresh")
    except Exception as e:
        logger.warning(f"⚠️ Could not clear news before refresh: {e}")

    result = news_routes.news_service.refresh_cache(force=True)
    try:
        metrics_model.inc_news_refresh()
    except Exception:
        pass
    return result


@router.get("/metrics")
async def get_system_metrics(email: Optional[str] = Query(None), x_admin_email: Optional[str] = Header(None, convert_underscores=False)):
    """Return usage/cost estimates and platform stats (admin only)."""
    _require_admin((email or x_admin_email or ""))
    usage = metrics_model.get()
    users = auth_db.get_user_stats() if auth_db else {}
    news_count = news_model.get_article_count() if news_model else 0
    chat_stats = chat_db.get_stats() if chat_db else {}
    return {
        "usage": usage,
        "users": users,
        "news": {"articles": news_count},
        "chat": chat_stats,
    }
