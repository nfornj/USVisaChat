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
from pydantic import BaseModel
import uvicorn
from datetime import datetime, timedelta
import uuid
from PIL import Image
import io
import requests
import os
import threading
import time
import hashlib
from dotenv import load_dotenv

# Load environment variables from .env file (standard production practice)
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from services.simple_vector_processor import SimpleVectorProcessor
from services.chat_synthesizer import ChatSynthesizer
from services.enhanced_chat_synthesizer import EnhancedChatSynthesizer
from models.community_chat import chat_manager
from models.user_auth import auth_db_instance as auth_db

def generate_comprehensive_ai_summary(title: str, content: str) -> str:
    """
    Generate intelligent AI summary using Groq LLM based on article content
    """
    groq_api_key = os.getenv('GROQ_API_KEY')
    
    # Fallback to simple summary if no API key
    if not groq_api_key:
        logger.warning("No GROQ_API_KEY found, using fallback summary")
        return generate_fallback_summary(content)
    
    try:
        # Prepare content for summarization (limit to 2000 chars to avoid token limits)
        article_text = f"{title}\n\n{content[:2000]}"
        
        # Call Groq API for intelligent summarization
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {groq_api_key}'
        }
        
        payload = {
            'model': 'llama-3.1-8b-instant',
            'messages': [{
                'role': 'system',
                'content': 'You are an immigration news expert. Summarize articles into 3-5 concise bullet points (each max 120 chars). Focus on key facts, dates, and actionable information. Start each point with • symbol. No introductions or conclusions.'
            }, {
                'role': 'user',
                'content': f'Summarize this H1B/immigration article into 3-5 bullet points:\n\n{article_text}'
            }],
            'temperature': 0.3,
            'max_tokens': 300
        }
        
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            summary = data['choices'][0]['message']['content'].strip()
            logger.info(f"✅ Generated AI summary using Groq")
            return summary
        else:
            logger.error(f"Groq API error: {response.status_code}")
            return generate_fallback_summary(content)
            
    except Exception as e:
        logger.error(f"Error generating AI summary with Groq: {e}")
        return generate_fallback_summary(content)

def generate_fallback_summary(content: str) -> str:
    """
    Fallback summary when Groq API is unavailable
    """
    sentences = content.split('. ')
    bullet_points = []
    
    for sentence in sentences[:3]:
        clean = sentence.strip()
        if len(clean) > 30 and not clean.startswith(('http', 'www')):
            if len(clean) > 120:
                clean = clean[:120] + '...'
            bullet_points.append(f"• {clean}")
    
    if len(bullet_points) < 2:
        bullet_points.append("• Latest immigration updates and news")
        bullet_points.append("• Important information for visa applicants")
    
    return '\n'.join(bullet_points[:4])

def generate_short_title(original_title: str, content: str) -> str:
    """
    Generate concise, punchy title using Groq (max 80 chars)
    """
    groq_api_key = os.getenv('GROQ_API_KEY')
    
    if not groq_api_key or len(original_title) < 80:
        return original_title[:80]
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {groq_api_key}'
        }
        
        payload = {
            'model': 'llama-3.1-8b-instant',
            'messages': [{
                'role': 'system',
                'content': 'You are a news headline writer. Create short, punchy headlines (max 80 chars). Be specific and actionable. Return ONLY the headline, no quotes or explanations.'
            }, {
                'role': 'user',
                'content': f'Create a short headline for this:\n\nTitle: {original_title}\n\nContent: {content[:500]}'
            }],
            'temperature': 0.3,
            'max_tokens': 50
        }
        
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            title = data['choices'][0]['message']['content'].strip()
            # Remove quotes if LLM added them
            title = title.strip('"\'')
            return title[:80]
        else:
            return original_title[:80]
            
    except Exception as e:
        logger.error(f"Error generating short title: {e}")
        return original_title[:80]

def generate_image_search_topic(title: str, content: str) -> str:
    """
    Generate focused image search topic using Groq (2-4 words)
    """
    groq_api_key = os.getenv('GROQ_API_KEY')
    
    if not groq_api_key:
        # Fallback to keyword extraction
        text = f"{title} {content}".lower()
        if 'h1b' in text or 'work visa' in text:
            return "h1b visa immigration"
        elif 'green card' in text:
            return "green card permanent residence"
        elif 'uscis' in text:
            return "uscis government office"
        return "immigration visa"
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {groq_api_key}'
        }
        
        payload = {
            'model': 'llama-3.1-8b-instant',
            'messages': [{
                'role': 'system',
                'content': 'Extract 2-4 keywords for image search from immigration news. Return ONLY keywords separated by spaces, no explanations. Focus on: visa types, government agencies, processes.'
            }, {
                'role': 'user',
                'content': f'{title}\n\n{content[:300]}'
            }],
            'temperature': 0.3,
            'max_tokens': 20
        }
        
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            topic = data['choices'][0]['message']['content'].strip()
            return topic[:50]  # Limit to 50 chars
        else:
            return "immigration visa"
            
    except Exception as e:
        logger.error(f"Error generating image topic: {e}")
        return "immigration visa"

# Image search and caching system
image_cache = {}
IMAGE_CACHE_EXPIRY_HOURS = 24 * 7  # 7 days cache for images

def get_google_search_image(title: str, content: str, index: int) -> str:
    """
    Get relevant image using Google Custom Search API with caching
    """
    # Create a cache key based on content
    cache_key = hashlib.md5(f"{title}_{content}".encode()).hexdigest()
    
    # Check if image is in cache and not expired
    if cache_key in image_cache:
        cached_data = image_cache[cache_key]
        if datetime.now() - cached_data['timestamp'] < timedelta(hours=IMAGE_CACHE_EXPIRY_HOURS):
            return cached_data['image_url']
    
    # Generate search query based on content
    search_query = generate_image_search_query(title, content)
    
    # Get image from Google Custom Search API with index for variety
    image_url = fetch_google_search_image(search_query, index)
    
    # Cache the result
    image_cache[cache_key] = {
        'image_url': image_url,
        'timestamp': datetime.now()
    }
    
    return image_url

def generate_image_search_query(title: str, content: str) -> str:
    """
    Generate optimized search query for Google Custom Search
    """
    text = f"{title} {content}".lower()
    
    # Base immigration-related terms
    base_terms = ["immigration", "visa", "h1b", "green card", "uscis"]
    
    # Specific terms based on content
    specific_terms = []
    
    if any(keyword in text for keyword in ['h1b', 'h-1b', 'work visa']):
        specific_terms.extend(["h1b visa", "work visa", "employment"])
    
    if any(keyword in text for keyword in ['green card', 'permanent residence', 'eb-2', 'eb-3']):
        specific_terms.extend(["green card", "permanent residence", "immigration"])
    
    if any(keyword in text for keyword in ['processing', 'timeline', 'wait time']):
        specific_terms.extend(["immigration processing", "government office"])
    
    if any(keyword in text for keyword in ['uscis', 'government', 'policy']):
        specific_terms.extend(["uscis", "government building", "immigration office"])
    
    if any(keyword in text for keyword in ['law', 'legal', 'regulation']):
        specific_terms.extend(["immigration law", "legal documents", "court"])
    
    # Combine terms and create search query
    all_terms = base_terms + specific_terms[:3]  # Limit to avoid long queries
    query = " ".join(all_terms[:5])  # Limit to 5 terms max
    
    return query

def fetch_google_search_image(query: str, index: int = 0) -> str:
    """
    Fetch image from Google Images API or fallback to curated images
    """
    google_api_key = os.getenv('GOOGLE_API_KEY')
    google_search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
    
    # Always use fallback for now - more reliable and consistent
    if not google_api_key or not google_search_engine_id:
        return get_fallback_image(query, index)
    
    try:
        # Use Google Custom Search API
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'q': query,
            'searchType': 'image',
            'key': google_api_key,
            'cx': google_search_engine_id,
            'num': 1,
            'safe': 'active',
            'imgSize': 'large',
            'imgType': 'photo',
            'fileType': 'jpg,png',
            'rights': 'cc_publicdomain,cc_attribute,cc_sharealike'
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                image_url = data['items'][0]['link']
                logger.info(f"Found image from Google: {image_url}")
                return image_url
        
        logger.warning(f"Google API returned no results, using fallback")
        return get_fallback_image(query, index)
            
    except Exception as e:
        logger.error(f"Google Images API error: {e}")
        return get_fallback_image(query, index)

def get_fallback_image(query: str, index: int = 0) -> str:
    """
    Intelligent fallback to high-quality Unsplash images based on query and index for variety
    """
    text = query.lower()
    
    # Diverse immigration-related image pool
    image_categories = {
        'h1b_visa': [
            "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800&h=400&fit=crop&auto=format&q=80",  # Business office
            "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&h=400&fit=crop&auto=format&q=80",  # City skyline
            "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&h=400&fit=crop&auto=format&q=80",  # Office workspace
        ],
        'green_card': [
            "https://images.unsplash.com/photo-1582213782179-e0d6f3ad0f95?w=800&h=400&fit=crop&auto=format&q=80",  # US Flag
            "https://images.unsplash.com/photo-1569098644584-210bcd375b59?w=800&h=400&fit=crop&auto=format&q=80",  # Statue of Liberty
            "https://images.unsplash.com/photo-1444858345149-8ff40887589b?w=800&h=400&fit=crop&auto=format&q=80",  # American landscape
        ],
        'government': [
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=400&fit=crop&auto=format&q=80",  # Government building
            "https://images.unsplash.com/photo-1479142506502-19b3a3b7ff33?w=800&h=400&fit=crop&auto=format&q=80",  # Capitol building
            "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=800&h=400&fit=crop&auto=format&q=80",  # Court/legal building
        ],
        'legal': [
            "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&h=400&fit=crop&auto=format&q=80",  # Legal documents
            "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=800&h=400&fit=crop&auto=format&q=80",  # Law books
            "https://images.unsplash.com/photo-1505664194779-8beaceb93744?w=800&h=400&fit=crop&auto=format&q=80",  # Legal office
        ],
        'work': [
            "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=800&h=400&fit=crop&auto=format&q=80",  # Modern office
            "https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=800&h=400&fit=crop&auto=format&q=80",  # Professionals working
            "https://images.unsplash.com/photo-1556761175-4b46a572b786?w=800&h=400&fit=crop&auto=format&q=80",  # Tech office
        ],
        'default': [
            "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=800&h=400&fit=crop&auto=format&q=80",  # Professional building
            "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&h=400&fit=crop&auto=format&q=80",  # City view
            "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&h=400&fit=crop&auto=format&q=80",  # Business charts
        ]
    }
    
    # Select category based on keywords
    if any(keyword in text for keyword in ['h1b', 'h-1b', 'visa', 'work visa']):
        images = image_categories['h1b_visa']
    elif any(keyword in text for keyword in ['green card', 'permanent', 'eb-2', 'eb-3']):
        images = image_categories['green_card']
    elif any(keyword in text for keyword in ['uscis', 'government', 'department']):
        images = image_categories['government']
    elif any(keyword in text for keyword in ['law', 'legal', 'policy', 'regulation']):
        images = image_categories['legal']
    elif any(keyword in text for keyword in ['employment', 'job', 'work', 'career']):
        images = image_categories['work']
    else:
        images = image_categories['default']
    
    # Use index to rotate through images
    return images[index % len(images)]

from services.email_service import email_service
from qdrant_client import QdrantClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global cache for AI News
ai_news_cache = {
    "articles": [],
    "last_updated": None,
    "last_api_fetch": None,  # Track last actual API call to Perplexity
    "is_fetching": False
}

# Cache settings
CACHE_EXPIRY_HOURS = 24
MAX_CACHED_ARTICLES = 10  # Keep maximum 10 articles
MIN_FETCH_INTERVAL_HOURS = 24  # Minimum 24 hours between API calls

def fetch_news_from_perplexity():
    """Fetch H1B news from Perplexity Search API (rate-limited to once per 24 hours)"""
    try:
        # Check if we've called the API in the last 24 hours
        if ai_news_cache["last_api_fetch"]:
            hours_since_fetch = (datetime.now() - ai_news_cache["last_api_fetch"]).total_seconds() / 3600
            if hours_since_fetch < MIN_FETCH_INTERVAL_HOURS:
                logger.info(f"⏳ Perplexity API called {hours_since_fetch:.1f}h ago. Skipping (minimum {MIN_FETCH_INTERVAL_HOURS}h interval)")
                return None
        
        perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        if not perplexity_api_key:
            logger.warning("Perplexity API key not configured")
            return None
            
        headers = {
            'Authorization': f'Bearer {perplexity_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "query": "H1B visa breaking news updates green card processing EB-2 EB-3 priority dates PERM labor certification I-140 I-485 processing times USCIS policy changes premium processing delays RFE responses visa bulletin employment-based immigration OPT STEM extension cap gap H-4 EAD work authorization",
            "max_results": 15,
            "search_domain_filter": [
                "immihelp.com",
                "redbus2us.com", 
                "travel.state.gov",
                "uscis.gov",
                "immigration.com",
                "myvisajobs.com",
                "h1bdata.info",
                "visajourney.com",
                "lawandborder.com",
                "nolo.com",
                "alllaw.com",
                "avvo.com"
            ],
            "max_tokens_per_page": 2048,
            "country": "US"
        }
        
        logger.info("Fetching H1B news from Perplexity Search API...")
        response = requests.post(
            "https://api.perplexity.ai/search",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
            return None
            
        data = response.json()
        # Track successful API call
        ai_news_cache["last_api_fetch"] = datetime.now()
        logger.info(f"✅ Successfully fetched {len(data.get('results', []))} news articles from Perplexity")
        return data
        
    except Exception as e:
        logger.error(f"Error fetching news from Perplexity: {e}")
        return None

def merge_articles_intelligently(new_articles, existing_articles):
    """
    Merge new articles with existing cache intelligently:
    - Keep latest articles first
    - Remove duplicates based on URL
    - Maintain MAX_CACHED_ARTICLES limit
    - Preserve article order (newest first)
    """
    if not new_articles:
        return existing_articles[:MAX_CACHED_ARTICLES]
    
    # Create a set of existing URLs for duplicate detection
    existing_urls = {article.get('url', '') for article in existing_articles}
    
    # Filter out duplicates from new articles
    unique_new_articles = [
        article for article in new_articles 
        if article.get('url', '') not in existing_urls
    ]
    
    # Combine existing and new articles
    all_articles = unique_new_articles + existing_articles
    
    # Sort by published date (newest first)
    all_articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
    
    # Keep only the most recent articles up to MAX_CACHED_ARTICLES
    return all_articles[:MAX_CACHED_ARTICLES]

def process_perplexity_results(perplexity_data):
    """Process Perplexity search results into our article format"""
    if not perplexity_data or 'results' not in perplexity_data:
        return []
    
    articles = []
    for i, result in enumerate(perplexity_data['results'][:12]):  # Limit to 12 articles
        try:
            # Extract information from Perplexity result
            original_title = result.get('title', f'H1B Visa News Update #{i+1}')
            content = result.get('content', result.get('snippet', ''))
            url = result.get('url', f'https://example.com/h1b-news/{i+1}')
            published_at = result.get('published_date', datetime.now().isoformat())
            source = result.get('site', 'Immigration News')
            
            # Generate SHORT title using Groq
            short_title = generate_short_title(original_title, content)
            
            # Generate AI summary
            ai_summary = generate_comprehensive_ai_summary(original_title, content)
            
            # Generate focused image search topic
            image_topic = generate_image_search_topic(original_title, content)
            
            article = {
                "id": f"article-{i}",
                "title": short_title,  # Use short AI-generated title
                "summary": content[:300] + "..." if len(content) > 300 else content,
                "content": content,
                "url": url,
                "publishedAt": published_at,
                "source": source,
                "imageUrl": get_fallback_image(image_topic, i),  # Use AI topic for better images
                "aiSummary": ai_summary,
                "tags": ["H1B", "Visa", "Immigration", "Work Visa", "Tech Industry"]
            }
            articles.append(article)
            
        except Exception as e:
            logger.error(f"Error processing article {i}: {e}")
            continue
    
    return articles

def background_news_fetcher():
    """Background task to fetch news daily"""
    while True:
        try:
            # Check if cache is expired or empty
            now = datetime.now()
            if (ai_news_cache["last_updated"] is None or 
                (now - ai_news_cache["last_updated"]).total_seconds() > CACHE_EXPIRY_HOURS * 3600):
                
                if not ai_news_cache["is_fetching"]:
                    ai_news_cache["is_fetching"] = True
                    logger.info("Starting background news fetch...")
                    
                    # Fetch from Perplexity
                    perplexity_data = fetch_news_from_perplexity()
                    
                    if perplexity_data:
                        new_articles = process_perplexity_results(perplexity_data)
                        if new_articles:
                            # Merge new articles with existing cache intelligently
                            merged_articles = merge_articles_intelligently(
                                new_articles, 
                                ai_news_cache["articles"]
                            )
                            ai_news_cache["articles"] = merged_articles
                            ai_news_cache["last_updated"] = now
                            
                            new_count = len([a for a in new_articles if a.get('url', '') not in {e.get('url', '') for e in ai_news_cache["articles"]}])
                            logger.info(f"✅ Updated cache with {len(merged_articles)} total articles ({new_count} new)")
                        else:
                            logger.warning("No articles processed from Perplexity data")
                    else:
                        logger.warning("Failed to fetch from Perplexity, keeping existing cache")
                    
                    ai_news_cache["is_fetching"] = False
                else:
                    logger.info("News fetch already in progress, skipping...")
            else:
                logger.info("Cache is still fresh, skipping fetch")
                
        except Exception as e:
            logger.error(f"Error in background news fetcher: {e}")
            ai_news_cache["is_fetching"] = False
        
        # Sleep for 1 hour before checking again
        time.sleep(3600)

def start_background_scheduler():
    """Start the background news fetcher in a separate thread"""
    def run_scheduler():
        background_news_fetcher()
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("🚀 Background news scheduler started")

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

class EditMessageRequest(BaseModel):
    message_id: str
    new_content: str
    user_email: str

# Initialize FastAPI app and API router
from fastapi import APIRouter

app = FastAPI(
    title="Visa Conversation MCP Server",
    description="MCP server exposing 767,253+ visa conversations for AI assistants",
    version="1.0.0"
)

# Create API router without prefix (handled by vite proxy)
api_router = APIRouter()

# Add CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)

# Backend API only - no frontend serving
# Frontend is served separately by Vite dev server

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
        
        # Start background news scheduler
        start_background_scheduler()
        
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

@app.post("/api/ai-news")
async def get_ai_news(request: SearchRequest):
    """
    AI News endpoint that returns cached H1B news or fetches fresh data if cache is empty
    """
    try:
        # Check if we have cached articles
        if ai_news_cache["articles"]:
            logger.info(f"Returning {len(ai_news_cache['articles'])} cached articles")
            articles = ai_news_cache["articles"][:request.limit or 10]
            
            return {
                "articles": articles,
                "total": len(articles),
                "query": f"{request.query} H1B visa news latest updates 2024",
                "timestamp": ai_news_cache["last_updated"].isoformat() if ai_news_cache["last_updated"] else datetime.now().isoformat(),
                "source": "cache",
                "cache_age_hours": round((datetime.now() - ai_news_cache["last_updated"]).total_seconds() / 3600, 1) if ai_news_cache["last_updated"] else 0
            }
        
        # If no cache, try to fetch fresh data
        logger.info("No cached articles found, fetching fresh data...")
        
        if not ai_news_cache["is_fetching"]:
            ai_news_cache["is_fetching"] = True
            
            # Fetch from Perplexity
            perplexity_data = fetch_news_from_perplexity()
            
        if perplexity_data:
            new_articles = process_perplexity_results(perplexity_data)
            if new_articles:
                # Merge new articles with existing cache intelligently
                merged_articles = merge_articles_intelligently(
                    new_articles, 
                    ai_news_cache["articles"]
                )
                ai_news_cache["articles"] = merged_articles
                ai_news_cache["last_updated"] = datetime.now()
                ai_news_cache["is_fetching"] = False
                
                new_count = len([a for a in new_articles if a.get('url', '') not in {e.get('url', '') for e in ai_news_cache["articles"]}])
                logger.info(f"✅ Fetched and cached {len(merged_articles)} total articles ({new_count} new)")
                
                return {
                    "articles": merged_articles[:request.limit or 10],
                    "total": len(merged_articles),
                    "query": f"{request.query} H1B visa news latest updates 2024",
                    "timestamp": datetime.now().isoformat(),
                    "source": "fresh_fetch"
                }
        
        ai_news_cache["is_fetching"] = False
        
        # If all else fails, return mock data
        logger.warning("No cache and fetch failed, returning mock data")
        
        mock_articles = [
            {
                "id": f"article-{i}",
                "title": f"H1B Visa Processing Updates: New Guidelines for 2024 #{i+1}",
                "summary": f"Latest developments in H1B visa processing and policy changes affecting international workers in the tech industry.",
                "content": f"Recent updates to H1B visa processing have introduced new guidelines that affect thousands of international workers. The changes focus on streamlining the application process while maintaining security standards. Key updates include revised documentation requirements and updated processing timelines that aim to reduce wait times for qualified applicants.",
                "url": f"https://example.com/h1b-news/{i+1}",
                "publishedAt": (datetime.now() - timedelta(hours=i*3)).isoformat(),
                "source": f"Immigration News {i+1}",
                "imageUrl": get_google_search_image(
                    f"H1B Visa Processing Updates - Latest News {i+1}",
                    f"Recent updates to H1B visa processing have introduced new guidelines that affect thousands of international workers. The changes focus on streamlining the application process while maintaining security standards. Key updates include revised documentation requirements and updated processing timelines that aim to reduce wait times for qualified applicants.",
                    i
                ),
                "aiSummary": generate_comprehensive_ai_summary(
                    f"H1B Visa Processing Updates - Latest News {i+1}",
                    f"Recent updates to H1B visa processing have introduced new guidelines that affect thousands of international workers. The changes focus on streamlining the application process while maintaining security standards. Key updates include revised documentation requirements and updated processing timelines that aim to reduce wait times for qualified applicants."
                ),
                "tags": ["H1B", "Visa", "Immigration", "Work Visa", "Tech Industry"]
            }
            for i in range(min(request.limit or 8, 10))
        ]
        
        return {
            "articles": mock_articles,
            "total": len(mock_articles),
            "query": f"{request.query} H1B visa news latest updates 2024",
            "timestamp": datetime.now().isoformat(),
            "source": "mock_data",
            "note": "Using mock data - Perplexity API unavailable"
        }
        
    except Exception as e:
        logger.error(f"❌ AI News error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch AI news: {str(e)}")

@app.get("/api/ai-news/status")
async def get_news_cache_status():
    """Get the current status of the news cache"""
    try:
        cache_age_hours = 0
        if ai_news_cache["last_updated"]:
            cache_age_hours = round((datetime.now() - ai_news_cache["last_updated"]).total_seconds() / 3600, 1)
        
        return {
            "cache_status": {
                "has_articles": len(ai_news_cache["articles"]) > 0,
                "article_count": len(ai_news_cache["articles"]),
                "last_updated": ai_news_cache["last_updated"].isoformat() if ai_news_cache["last_updated"] else None,
                "cache_age_hours": cache_age_hours,
                "is_fetching": ai_news_cache["is_fetching"],
                "is_expired": cache_age_hours > CACHE_EXPIRY_HOURS if ai_news_cache["last_updated"] else True
            }
        }
    except Exception as e:
        logger.error(f"❌ Cache status error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache status: {str(e)}")

@app.post("/api/ai-news/refresh")
async def refresh_news_cache():
    """Manually trigger a news cache refresh"""
    try:
        if ai_news_cache["is_fetching"]:
            return {"message": "News fetch already in progress", "status": "fetching"}
        
        ai_news_cache["is_fetching"] = True
        logger.info("Manual news refresh triggered...")
        
        # Fetch from Perplexity
        perplexity_data = fetch_news_from_perplexity()
        
        if perplexity_data:
            new_articles = process_perplexity_results(perplexity_data)
            if new_articles:
                # Merge new articles with existing cache intelligently
                merged_articles = merge_articles_intelligently(
                    new_articles, 
                    ai_news_cache["articles"]
                )
                ai_news_cache["articles"] = merged_articles
                ai_news_cache["last_updated"] = datetime.now()
                ai_news_cache["is_fetching"] = False
                
                new_count = len([a for a in new_articles if a.get('url', '') not in {e.get('url', '') for e in ai_news_cache["articles"]}])
                return {
                    "message": f"Successfully refreshed cache with {len(merged_articles)} total articles ({new_count} new)",
                    "status": "success",
                    "article_count": len(merged_articles)
                }
        
        ai_news_cache["is_fetching"] = False
        return {"message": "Failed to fetch fresh news", "status": "failed"}
        
    except Exception as e:
        logger.error(f"❌ Manual refresh error: {e}")
        ai_news_cache["is_fetching"] = False
        raise HTTPException(status_code=500, detail=f"Failed to refresh news: {str(e)}")


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
            message=f"Verification code sent to {request.email}. Check your email (or server logs in DEV MODE). Code: {code}",
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

# Community Chat WebSocket endpoint - Using simple path to avoid routing issues
@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time community chat with room isolation"""
    # MUST accept connection FIRST before doing anything
    await websocket.accept()
    
    # Now get parameters from query string
    query_params = dict(websocket.query_params)
    user_email = query_params.get("user_email", "")
    display_name = query_params.get("display_name", "")
    room_id = query_params.get("room_id", "general")
    
    logger.info(f"🔌 WebSocket connected: email={user_email}, name={display_name}, room={room_id}")
    
    if not user_email or not display_name:
        logger.error("❌ Missing user_email or display_name")
        await websocket.close(code=1008, reason="Missing required parameters")
        return
    
    try:
        # Register with chat manager (don't call accept again inside!)
        # Store connection in our room structure
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
        
        # Notify others
        await chat_manager.broadcast_system_message(f"{display_name} joined the chat", room_id=room_id, exclude=user_email)
        await chat_manager.broadcast_user_list(room_id)
        
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
        chat_manager.disconnect(user_email, room_id)
        await chat_manager.broadcast_system_message(f"{display_name} left the chat", room_id=room_id)
        await chat_manager.broadcast_user_list(room_id)
    except Exception as e:
        logger.error(f"WebSocket error for {user_email} in room {room_id}: {e}")
        chat_manager.disconnect(user_email, room_id)

@app.get("/chat/history")
async def get_chat_history(limit: int = 50, room_id: str = "general"):
    """Get recent chat history for a specific room"""
    try:
        messages = chat_manager.db.get_recent_messages(limit=limit, room_id=room_id)
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@app.post("/chat/edit-message")
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

@app.get("/chat/users")
async def get_online_users(room_id: str = "general"):
    """Get list of currently online users in a specific room"""
    if room_id in chat_manager.rooms:
        users = list(chat_manager.rooms[room_id].keys())
        return {"users": users, "count": len(users), "room_id": room_id}
    return {"users": [], "count": 0, "room_id": room_id}

# Serve React frontend
from fastapi.responses import FileResponse
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")
    logger.info("✅ Serving React frontend from /")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve React app for all non-API routes"""
        # Skip API routes
        if full_path.startswith(("api/", "health", "search", "stats", "chat/", "auth/", "media/", "docs", "openapi.json")):
            return {"detail": "Not Found"}
        
        # Serve index.html for all other routes (React routing)
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"detail": "Frontend not found"}
else:
    logger.warning("⚠️  Frontend dist directory not found, serving API only")

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the MCP server with frontend"""
    logger.info(f"🚀 Starting Visa MCP Server on {host}:{port}")
    logger.info("🔍 Exposing 767,253+ visa conversations to AI assistants")
    logger.info("✅ Serving React frontend from /")
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    run_server()
