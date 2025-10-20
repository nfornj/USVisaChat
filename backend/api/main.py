"""
MCP Server for Visa Vector Database
Exposes 767,253+ visa conversations to AI assistants via Model Context Protocol
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import uuid
from PIL import Image
import io

from services.simple_vector_processor import SimpleVectorProcessor
from services.chat_synthesizer import ChatSynthesizer
from services.enhanced_chat_synthesizer import EnhancedChatSynthesizer
from models.community_chat import chat_manager
from models.user_auth import auth_db_instance as auth_db
from services.email_service import email_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API
class SearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 10

class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_found: int
    processing_time_ms: int

class StatsResponse(BaseModel):
    collection_name: str
    total_vectors: int
    status: str
    vector_dimensions: int
    embedding_model: str

class HealthResponse(BaseModel):
    status: str
    message: str
    version: str

# Authentication models
class AuthRequestCodeRequest(BaseModel):
    email: str
    display_name: str

class AuthRequestCodeResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[str] = None  # MongoDB uses ObjectId strings, not integers

class AuthVerifyCodeRequest(BaseModel):
    email: str
    code: str

class AuthVerifyCodeResponse(BaseModel):
    success: bool
    message: str
    session_token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None

class UpdateProfileRequest(BaseModel):
    session_token: str
    display_name: str

class UpdateProfileResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None

# Initialize FastAPI app
app = FastAPI(
    title="Visa Conversation MCP Server",
    description="MCP server exposing 767,253+ visa conversations for AI assistants",
    version="1.0.0"
)

# Add CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend (if built)
# Path is relative to /app (project root), not to backend/api/
FRONTEND_BUILD_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"
if FRONTEND_BUILD_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_BUILD_DIR / "assets")), name="static")

# Create and mount media directory for uploaded images
MEDIA_DIR = Path(__file__).parent.parent.parent / "data" / "media" / "chat_images"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR.parent)), name="media")

# Global instances
vector_processor = None
chat_synthesizer = ChatSynthesizer()
enhanced_synthesizer = EnhancedChatSynthesizer()  # New: RedBus2US knowledge-based answers

@app.on_event("startup")
async def startup_event():
    """Initialize vector processor on startup"""
    global vector_processor
    logger.info("🚀 Starting Visa MCP Server...")
    
    try:
        # Create processor instance (will initialize lazily on first use)
        vector_processor = SimpleVectorProcessor()
        logger.info("✅ Vector processor created (will initialize on first request)")
    except Exception as e:
        logger.error(f"❌ Failed to create vector processor: {e}")
        raise

@app.get("/health", response_model=HealthResponse)
async def detailed_health():
    """Detailed health check with database status"""
    try:
        # Check Qdrant connection
        qdrant = QdrantClient(host="qdrant", port=6333)
        collections = qdrant.get_collections()
        
        # Check if our collection exists
        redbus_collection_exists = any(c.name == "redbus2us_articles" for c in collections.collections)
        
        if not redbus_collection_exists:
            raise HTTPException(status_code=503, detail="RedBus2US articles collection not found")
        
        # Get collection info
        collection_info = qdrant.get_collection("redbus2us_articles")
        points_count = collection_info.points_count
        
        return HealthResponse(
            status="healthy",
            message=f"Connected to Qdrant with {points_count} RedBus2US article vectors",
            version="1.0.0"
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.post("/search", response_model=SearchResponse)
async def search_conversations(request: SearchRequest):
    """Search visa conversations using semantic search"""
    global vector_processor
    
    if not vector_processor or not vector_processor.is_initialized:
        raise HTTPException(status_code=503, detail="Vector processor not initialized")
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Perform semantic search
        results = await vector_processor.semantic_search(
            query=request.query,
            filters=request.filters,
            limit=request.limit
        )
        
        end_time = asyncio.get_event_loop().time()
        processing_time_ms = int((end_time - start_time) * 1000)
        
        return SearchResponse(
            query=request.query,
            results=results,
            total_found=len(results),
            processing_time_ms=processing_time_ms
        )
        
    except Exception as e:
        logger.error(f"❌ Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/stats", response_model=StatsResponse)
async def get_collection_stats():
    """Get vector collection statistics"""
    global vector_processor
    
    if not vector_processor or not vector_processor.is_initialized:
        raise HTTPException(status_code=503, detail="Vector processor not initialized")
    
    try:
        stats = await vector_processor.get_collection_stats()
        
        if 'error' in stats:
            raise HTTPException(status_code=500, detail=stats['error'])
        
        return StatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"❌ Stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/search/categories")
async def get_available_categories():
    """Get available visa categories for filtering"""
    return {
        "visa_types": ["h1b", "f1", "l1", "b1b2", "h4"],
        "categories": [
            "dropbox_eligibility",
            "interview_experience", 
            "document_requirements",
            "processing_times",
            "visa_status",
            "emergency_appointment",
            "appointment_scheduling"
        ],
        "locations": ["mumbai", "delhi", "chennai", "hyderabad", "kolkata", "bangalore"]
    }

@app.get("/search/examples")
async def get_search_examples():
    """Get example search queries for demonstration"""
    return {
        "examples": [
            {
                "query": "H1B dropbox eligibility requirements",
                "description": "Find information about H1B visa dropbox eligibility"
            },
            {
                "query": "F1 student visa interview experience",
                "description": "Search for F1 visa interview experiences"
            },
            {
                "query": "Emergency appointment urgent travel",
                "description": "Find information about emergency visa appointments"
            },
            {
                "query": "Mumbai consulate processing time",
                "description": "Search for processing times at Mumbai consulate"
            },
            {
                "query": "Administrative processing 221g timeline",
                "description": "Find information about 221g administrative processing"
            }
        ]
    }

@app.post("/chat")
async def chat_with_synthesis(request: SearchRequest):
    """Chat endpoint with synthesized responses"""
    global vector_processor, chat_synthesizer
    
    if not vector_processor or not vector_processor.is_initialized:
        raise HTTPException(status_code=503, detail="Vector processor not initialized")
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Perform semantic search with more results for better synthesis
        results = await vector_processor.semantic_search(
            query=request.query,
            filters=request.filters,
            limit=request.limit or 15  # Get more results for synthesis
        )
        
        # Synthesize the response
        synthesized_answer = chat_synthesizer.synthesize_response(
            query=request.query,
            results=results,
            total_found=len(results)
        )
        
        end_time = asyncio.get_event_loop().time()
        processing_time_ms = int((end_time - start_time) * 1000)
        
        return {
            "query": request.query,
            "answer": synthesized_answer,
            "results": results[:5],  # Return top 5 for source references
            "total_found": len(results),
            "processing_time_ms": processing_time_ms
        }
        
    except Exception as e:
        logger.error(f"❌ Chat synthesis error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/api/ai/ask")
async def ask_ai_with_redbus_knowledge(request: SearchRequest):
    """
    AI Assistant endpoint with RedBus2US authoritative knowledge
    Uses Qdrant to search H1B articles and generates intelligent answers with local LLM
    """
    global enhanced_synthesizer
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Generate answer using RedBus2US knowledge
        result = await enhanced_synthesizer.synthesize_answer(
            query=request.query,
            use_redbus=True
        )
        
        end_time = asyncio.get_event_loop().time()
        processing_time_ms = int((end_time - start_time) * 1000)
        
        return {
            "query": request.query,
            "answer": result["answer"],
            "sources": result["sources"],
            "confidence": result["confidence"],
            "type": result["type"],
            "articles_found": result.get("articles_found", 0),
            "processing_time_ms": processing_time_ms
        }
        
    except Exception as e:
        logger.error(f"❌ AI ask error: {e}")
        raise HTTPException(status_code=500, detail=f"AI query failed: {str(e)}")


# Authentication endpoints
@app.post("/auth/request-code", response_model=AuthRequestCodeResponse)
async def request_verification_code(request: AuthRequestCodeRequest):
    """Request a verification code to be sent to email"""
    try:
        # Create or get user
        user = auth_db.create_or_get_user(request.email, request.display_name)
        
        # Generate verification code
        code = auth_db.create_verification_code(user['id'], expires_in_minutes=10)
        
        # Send email with code
        email_sent = email_service.send_verification_code(request.email, code, request.display_name)
        
        if not email_sent:
            raise HTTPException(status_code=500, detail="Failed to send verification email")
        
        return AuthRequestCodeResponse(
            success=True,
            message=f"Verification code sent to {request.email}. Check your email (or server logs in DEV MODE).",
            user_id=user['id']
        )
    except Exception as e:
        logger.error(f"❌ Failed to create verification code: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send verification code: {str(e)}")

@app.post("/auth/verify-code", response_model=AuthVerifyCodeResponse)
async def verify_code(request: AuthVerifyCodeRequest):
    """Verify the code and create session"""
    try:
        # Verify code
        is_valid, user = auth_db.verify_code(request.email, request.code)
        
        if not is_valid or not user:
            return AuthVerifyCodeResponse(
                success=False,
                message="Invalid or expired verification code"
            )
        
        # Create session
        session_token = auth_db.create_session(user['id'], expires_in_days=30)
        
        logger.info(f"✅ User logged in: {request.email}")
        
        return AuthVerifyCodeResponse(
            success=True,
            message="Login successful",
            session_token=session_token,
            user={
                "id": user['id'],
                "email": user['email'],
                "display_name": user['display_name'],
                "is_verified": user['is_verified']
            }
        )
    except Exception as e:
        logger.error(f"❌ Code verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

@app.post("/auth/logout")
async def logout(session_token: str):
    """Logout and invalidate session"""
    try:
        auth_db.invalidate_session(session_token)
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"❌ Logout failed: {e}")
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")

@app.get("/auth/verify-session")
async def verify_session(session_token: str):
    """Verify if session is still valid"""
    try:
        user = auth_db.get_user_by_session(session_token)
        
        if user:
            return {
                "success": True,
                "user": {
                    "id": user['id'],
                    "email": user['email'],
                    "display_name": user['display_name'],
                    "is_verified": user['is_verified']
                }
            }
        else:
            return {"success": False, "message": "Invalid or expired session"}
    except Exception as e:
        logger.error(f"❌ Session verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Session verification failed: {str(e)}")

@app.post("/auth/update-profile", response_model=UpdateProfileResponse)
async def update_profile(request: UpdateProfileRequest):
    """Update user profile (display name)"""
    try:
        # Verify session first
        user = auth_db.get_user_by_session(request.session_token)
        
        if not user:
            return UpdateProfileResponse(
                success=False,
                message="Invalid or expired session"
            )
        
        # Update display name
        updated_user = auth_db.update_user_profile(user['id'], request.display_name)
        
        if updated_user:
            logger.info(f"✅ Profile updated for {user['email']}: {request.display_name}")
            return UpdateProfileResponse(
                success=True,
                message="Profile updated successfully",
                user={
                    "id": updated_user['id'],
                    "email": updated_user['email'],
                    "display_name": updated_user['display_name'],
                    "is_verified": updated_user['is_verified']
                }
            )
        else:
            return UpdateProfileResponse(
                success=False,
                message="Failed to update profile"
            )
    except Exception as e:
        logger.error(f"❌ Profile update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")

@app.get("/auth/stats")
async def get_auth_stats():
    """Get authentication statistics"""
    try:
        stats = auth_db.get_user_stats()
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to get auth stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

# Image upload endpoint
def compress_image(image_data: bytes, max_size: int = 600, quality: int = 40) -> bytes:
    """
    Compress and resize image to reduce file size (AGGRESSIVE compression for cost savings)
    - Resize to max 600px (much smaller for chat)
    - Convert to RGB if needed
    - Compress with 40% quality (optimized for file size)
    - Target: 5-20KB per image
    """
    try:
        # Open image
        img = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if needed
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            logger.info(f"📐 Resized image to {img.width}x{img.height}")
        
        # Compress
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        compressed_data = output.getvalue()
        
        original_size = len(image_data) / 1024  # KB
        compressed_size = len(compressed_data) / 1024  # KB
        logger.info(f"📦 Compressed image: {original_size:.1f}KB → {compressed_size:.1f}KB (saved {original_size - compressed_size:.1f}KB)")
        
        return compressed_data
    except Exception as e:
        logger.error(f"❌ Image compression failed: {e}")
        raise

@app.post("/chat/upload-image")
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

# MCP Protocol endpoints (simplified)
@app.post("/mcp/search")
async def mcp_search(request: SearchRequest):
    """MCP-compatible search endpoint"""
    try:
        search_result = await search_conversations(request)
        
        # Format for MCP protocol
        mcp_response = {
            "jsonrpc": "2.0",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"Found {search_result.total_found} visa conversations matching '{request.query}'"
                    }
                ],
                "results": search_result.results,
                "metadata": {
                    "query": search_result.query,
                    "processing_time_ms": search_result.processing_time_ms,
                    "source": "visa_conversations_database"
                }
            }
        }
        
        return mcp_response
        
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32000,
                "message": f"Search failed: {str(e)}"
            }
        }

@app.get("/mcp/capabilities")
async def mcp_capabilities():
    """MCP server capabilities"""
    return {
        "jsonrpc": "2.0",
        "result": {
            "capabilities": {
                "resources": {
                    "visa_conversations": {
                        "name": "visa_conversations",
                        "description": "767,253+ visa conversation database",
                        "mimeType": "application/json"
                    }
                },
                "tools": [
                    {
                        "name": "search_visa_conversations",
                        "description": "Search through visa conversations using semantic search",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query"},
                                "filters": {"type": "object", "description": "Optional filters"},
                                "limit": {"type": "integer", "description": "Maximum results to return"}
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        }
    }

# Community Chat WebSocket endpoint
@app.websocket("/ws/chat/{user_email}/{display_name}")
async def websocket_chat_endpoint(websocket: WebSocket, user_email: str, display_name: str):
    """WebSocket endpoint for real-time community chat"""
    # Use the actual display name from the user's profile, not auto-generated
    await chat_manager.connect(websocket, user_email, display_name)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle the message with actual display name
            await chat_manager.handle_message(user_email, display_name, data)
            
    except WebSocketDisconnect:
        chat_manager.disconnect(user_email)
        await chat_manager.broadcast_system_message(f"{display_name} left the chat")
        await chat_manager.broadcast_user_list()
    except Exception as e:
        logger.error(f"WebSocket error for {user_email}: {e}")
        chat_manager.disconnect(user_email)

@app.get("/chat/history")
async def get_chat_history(limit: int = 50):
    """Get recent chat history"""
    try:
        messages = chat_manager.db.get_recent_messages(limit=limit)
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@app.get("/chat/users")
async def get_online_users():
    """Get list of currently online users"""
    users = list(chat_manager.active_connections.keys())
    return {"users": users, "count": len(users)}

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve React frontend for all non-API routes"""
    # Skip API routes - don't handle them here at all
    if full_path.startswith(("search", "stats", "health", "mcp", "docs", "openapi.json", "redoc", "assets", "ws", "chat", "auth")):
        raise HTTPException(status_code=404, detail="Not found")
    
    # Serve root or other frontend routes
    if not FRONTEND_BUILD_DIR.exists():
        return {
            "message": "Frontend not built yet",
            "instructions": "Run 'cd frontend && npm install && npm run build' to build the frontend"
        }
    
    # Serve index.html for all routes (React Router)
    index_file = FRONTEND_BUILD_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        raise HTTPException(status_code=404, detail="Frontend build not found")

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the MCP server"""
    logger.info(f"🚀 Starting Visa MCP Server on {host}:{port}")
    logger.info("🔍 Exposing 767,253+ visa conversations to AI assistants")
    
    if FRONTEND_BUILD_DIR.exists():
        logger.info("✅ Serving React frontend from /")
    else:
        logger.warning("⚠️  Frontend not built - only API available")
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    run_server()
