"""
News Utilities
Helper functions for news processing, image handling, and AI summarization
"""

import logging
import hashlib
import requests
import os
from datetime import datetime, timedelta
from typing import Dict
from PIL import Image
import io

logger = logging.getLogger(__name__)

# Image cache for reducing API calls
image_cache: Dict[str, Dict] = {}
IMAGE_CACHE_EXPIRY_HOURS = 24 * 7  # 7 days


def generate_comprehensive_ai_summary(title: str, content: str) -> str:
    """
    Generate intelligent AI summary using Groq LLM based on article content
    """
    groq_api_key = os.getenv('GROQ_API_KEY')
    
    if not groq_api_key:
        logger.warning("No GROQ_API_KEY found, using fallback summary")
        return generate_fallback_summary(content)
    
    try:
        article_text = f"{title}\n\n{content[:2000]}"
        
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
            title = title.strip('"\'')
            return title[:80]
        else:
            return original_title[:80]
            
    except Exception as e:
        logger.error(f"Error generating short title: {e}")
        return original_title[:80]


def get_fallback_image(query: str, index: int = 0) -> str:
    """
    Intelligent fallback to high-quality Unsplash images based on query and index
    """
    text = query.lower()
    
    image_categories = {
        'h1b_visa': [
            "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800&h=400&fit=crop&auto=format&q=80",
            "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&h=400&fit=crop&auto=format&q=80",
            "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&h=400&fit=crop&auto=format&q=80",
        ],
        'green_card': [
            "https://images.unsplash.com/photo-1582213782179-e0d6f3ad0f95?w=800&h=400&fit=crop&auto=format&q=80",
            "https://images.unsplash.com/photo-1569098644584-210bcd375b59?w=800&h=400&fit=crop&auto=format&q=80",
            "https://images.unsplash.com/photo-1444858345149-8ff40887589b?w=800&h=400&fit=crop&auto=format&q=80",
        ],
        'government': [
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=400&fit=crop&auto=format&q=80",
            "https://images.unsplash.com/photo-1479142506502-19b3a3b7ff33?w=800&h=400&fit=crop&auto=format&q=80",
            "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=800&h=400&fit=crop&auto=format&q=80",
        ],
        'legal': [
            "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&h=400&fit=crop&auto=format&q=80",
            "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=800&h=400&fit=crop&auto=format&q=80",
            "https://images.unsplash.com/photo-1505664194779-8beaceb93744?w=800&h=400&fit=crop&auto=format&q=80",
        ],
        'work': [
            "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=800&h=400&fit=crop&auto=format&q=80",
            "https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=800&h=400&fit=crop&auto=format&q=80",
            "https://images.unsplash.com/photo-1556761175-4b46a572b786?w=800&h=400&fit=crop&auto=format&q=80",
        ],
        'default': [
            "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=800&h=400&fit=crop&auto=format&q=80",
            "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&h=400&fit=crop&auto=format&q=80",
            "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&h=400&fit=crop&auto=format&q=80",
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
    
    return images[index % len(images)]


def get_google_search_image(title: str, content: str, index: int) -> str:
    """
    Get relevant image using Google Custom Search API with caching
    """
    cache_key = hashlib.md5(f"{title}_{content}".encode()).hexdigest()
    
    if cache_key in image_cache:
        cached_data = image_cache[cache_key]
        if datetime.now() - cached_data['timestamp'] < timedelta(hours=IMAGE_CACHE_EXPIRY_HOURS):
            return cached_data['image_url']
    
    # Always use fallback for reliability
    google_api_key = os.getenv('GOOGLE_API_KEY')
    google_search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
    
    if not google_api_key or not google_search_engine_id:
        return get_fallback_image(f"{title} {content}", index)
    
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'q': f"{title} immigration visa",
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
                image_cache[cache_key] = {
                    'image_url': image_url,
                    'timestamp': datetime.now()
                }
                logger.info(f"Found image from Google: {image_url}")
                return image_url
        
        return get_fallback_image(f"{title} {content}", index)
            
    except Exception as e:
        logger.error(f"Google Images API error: {e}")
        return get_fallback_image(f"{title} {content}", index)


def compress_image(image_data: bytes, max_size: int = 600, quality: int = 40) -> bytes:
    """
    Compress and resize image to reduce file size
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            logger.info(f"📐 Resized image to {img.width}x{img.height}")
        
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        compressed_data = output.getvalue()
        
        original_size = len(image_data) / 1024
        compressed_size = len(compressed_data) / 1024
        logger.info(f"📦 Compressed image: {original_size:.1f}KB → {compressed_size:.1f}KB")
        
        return compressed_data
    except Exception as e:
        logger.error(f"❌ Image compression failed: {e}")
        raise
