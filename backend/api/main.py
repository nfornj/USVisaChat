"""
Visa Platform API - Refactored
Modular FastAPI application with clean separation of concerns
"""

import logging
from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Import route modules
from api.routes import auth_router, chat_router, search_router, news_router
from api.routes.chat import websocket_chat_handler
from api.routes.search import init_search_services
from api.routes.news import init_news_service

# Import services
from services.simple_vector_processor import SimpleVectorProcessor
from services.chat_synthesizer import ChatSynthesizer
from services.enhanced_chat_synthesizer import EnhancedChatSynthesizer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Visa Platform API",
    description="Modular API for visa conversations, AI search, and community chat",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instances
vector_processor = None
chat_synthesizer = ChatSynthesizer()
enhanced_synthesizer = EnhancedChatSynthesizer()


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global vector_processor
    
    logger.info("🚀 Starting Visa Platform API v2.0...")
    
    try:
        # Initialize vector processor
        vector_processor = SimpleVectorProcessor()
        logger.info("✅ Vector processor created (will initialize on first request)")
        
        # Initialize search services
        init_search_services(vector_processor, chat_synthesizer, enhanced_synthesizer)
        logger.info("✅ Search services initialized")
        
        # Initialize news service
        init_news_service()
        logger.info("✅ News service initialized")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise


# Register routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(search_router)
app.include_router(news_router)


# WebSocket endpoint (must be registered directly on app)
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time community chat"""
    await websocket_chat_handler(websocket)


# Media files
MEDIA_DIR = Path(__file__).parent.parent.parent / "data" / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


# Serve React frontend
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")
    logger.info("✅ Serving React frontend from /")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve React app for all non-API routes"""
        # Skip API routes
        if full_path.startswith((
            "api/", "health", "search", "stats", "chat/", "auth/", 
            "media/", "docs", "openapi.json", "ws/", "mcp/"
        )):
            return {"detail": "Not Found"}
        
        # Serve index.html for all other routes (React routing)
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"detail": "Frontend not found"}
else:
    logger.warning("⚠️  Frontend dist directory not found, serving API only")


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the Visa Platform API server"""
    logger.info(f"🚀 Starting Visa Platform API on {host}:{port}")
    logger.info("🔍 Exposing 767,253+ visa conversations to AI assistants")
    logger.info("✅ Modular architecture with clean separation of concerns")
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
