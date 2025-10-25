"""
Search Routes
Handles vector search, AI assistant, and MCP protocol endpoints
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException
from qdrant_client import QdrantClient

from api.schemas import SearchRequest, SearchResponse, StatsResponse, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])

# Global instances (injected from main.py)
vector_processor = None
chat_synthesizer = None
enhanced_synthesizer = None


def init_search_services(vp, cs, es):
    """Initialize search service dependencies"""
    global vector_processor, chat_synthesizer, enhanced_synthesizer
    vector_processor = vp
    chat_synthesizer = cs
    enhanced_synthesizer = es


@router.get("/health", response_model=HealthResponse)
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
            version="2.0.0"
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@router.post("/search", response_model=SearchResponse)
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


@router.get("/stats", response_model=StatsResponse)
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


@router.get("/search/categories")
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


@router.get("/search/examples")
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


@router.post("/chat")
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
            limit=request.limit or 15
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
            "results": results[:5],
            "total_found": len(results),
            "processing_time_ms": processing_time_ms
        }
        
    except Exception as e:
        logger.error(f"❌ Chat synthesis error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/api/ai/ask")
async def ask_ai_with_redbus_knowledge(request: SearchRequest):
    """
    AI Assistant endpoint with RedBus2US authoritative knowledge
    Uses Qdrant to search H1B articles and generates intelligent answers
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


@router.post("/mcp/search")
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


@router.get("/mcp/capabilities")
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
