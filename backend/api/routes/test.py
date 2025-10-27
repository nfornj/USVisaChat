"""
Test Routes
Endpoints for testing all service connections
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(tags=["testing"])


@router.get("/test-connections")
async def test_all_connections() -> Dict[str, Any]:
    """
    Test all service connections and return their status
    
    Returns detailed status for:
    - MongoDB (Atlas)
    - LLM Service (Groq/Ollama)
    - News Service (Perplexity)
    """
    results = {
        "timestamp": None,
        "overall_status": "healthy",
        "services": {}
    }
    
    from datetime import datetime
    results["timestamp"] = datetime.utcnow().isoformat()
    
    # Test MongoDB
    try:
        from models.mongodb_connection import mongodb_client
        if mongodb_client and mongodb_client.client:
            # Test connection
            mongodb_client.client.admin.command('ping')
            server_info = mongodb_client.client.server_info()
            stats = mongodb_client.get_stats()
            
            results["services"]["mongodb"] = {
                "status": "connected",
                "type": "MongoDB Atlas",
                "version": server_info.get('version', 'unknown'),
                "database": mongodb_client.database_name,
                "collections": stats.get('collections', {}),
                "total_documents": stats.get('total_documents', 0),
                "details": "MongoDB connection is healthy"
            }
        else:
            results["services"]["mongodb"] = {
                "status": "disconnected",
                "error": "MongoDB client not initialized"
            }
            results["overall_status"] = "degraded"
    except Exception as e:
        results["services"]["mongodb"] = {
            "status": "error",
            "error": str(e)
        }
        results["overall_status"] = "degraded"
    
    # Test LLM Service
    try:
        from services.llm_service import llm_service
        
        provider_info = llm_service.get_provider_info()
        
        results["services"]["llm"] = {
            "status": "configured",
            "provider": provider_info.get('provider'),
            "model": provider_info.get('model'),
            "host": provider_info.get('host'),
            "api_key_configured": provider_info.get('api_key_configured'),
            "details": "LLM service is configured and ready"
        }
    except Exception as e:
        results["services"]["llm"] = {
            "status": "error",
            "error": str(e)
        }
        results["overall_status"] = "degraded"
    
    # Test News Service
    try:
        from api.routes.news import news_service
        
        if news_service:
            results["services"]["news"] = {
                "status": "configured",
                "provider": "Perplexity AI",
                "details": "News service is initialized"
            }
        else:
            results["services"]["news"] = {
                "status": "not_initialized",
                "details": "News service not available"
            }
    except Exception as e:
        results["services"]["news"] = {
            "status": "error",
            "error": str(e)
        }
        # News service is optional, don't degrade overall status
    
    
    return results


@router.get("/test-mongodb")
async def test_mongodb_only() -> Dict[str, Any]:
    """Test MongoDB connection specifically with detailed diagnostics"""
    try:
        from models.mongodb_connection import mongodb_client
        
        if not mongodb_client or not mongodb_client.client:
            raise HTTPException(status_code=503, detail="MongoDB client not initialized")
        
        # Test connection
        mongodb_client.client.admin.command('ping')
        
        # Get server info
        server_info = mongodb_client.client.server_info()
        
        # Get database stats
        stats = mongodb_client.get_stats()
        
        # List all collections
        db = mongodb_client.db
        collection_names = db.list_collection_names()
        
        return {
            "status": "connected",
            "connection_type": "MongoDB Atlas",
            "server_version": server_info.get('version'),
            "database": mongodb_client.database_name,
            "collections": collection_names,
            "stats": stats,
            "connection_details": {
                "tls_enabled": mongodb_client.tls_enabled,
                "auth_mechanism": mongodb_client.auth_mechanism
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"MongoDB connection test failed: {str(e)}"
        )


@router.get("/test-qdrant")
async def test_qdrant_only() -> Dict[str, Any]:
    """Test Qdrant connection specifically"""
    try:
        from qdrant_client import QdrantClient
        import os
        
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        
        qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
        
        # Get all collections
        collections = qdrant.get_collections()
        
        collection_details = {}
        for collection in collections.collections:
            try:
                info = qdrant.get_collection(collection.name)
                collection_details[collection.name] = {
                    "points_count": info.points_count,
                    "config": {
                        "distance": str(info.config.params.vectors.distance) if hasattr(info.config.params, 'vectors') else "unknown"
                    }
                }
            except Exception as e:
                collection_details[collection.name] = {
                    "error": str(e)
                }
        
        return {
            "status": "connected",
            "host": f"{qdrant_host}:{qdrant_port}",
            "total_collections": len(collections.collections),
            "collections": collection_details
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Qdrant connection test failed: {str(e)}"
        )
