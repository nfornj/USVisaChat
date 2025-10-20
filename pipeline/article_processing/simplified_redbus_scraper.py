#!/usr/bin/env python3
"""
Simplified RedBus2US Article Scraper
Downloads articles with clean JSON structure and handles images properly.
"""

import asyncio
import aiohttp
import aiofiles
import json
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import hashlib
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimplifiedRedBusScraper:
    """Simplified RedBus2US scraper with clean JSON structure and image handling."""
    
    def __init__(self):
        self.base_url = "https://redbus2us.com"
        self.session = None
        
        # Output directories
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / "data" / "redbus2us_raw"
        self.articles_dir = self.data_dir / "articles"
        self.images_dir = self.data_dir / "images"
        
        # Create directories
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            'articles_scraped': 0,
            'articles_failed': 0,
            'images_downloaded': 0,
            'images_failed': 0,
            'start_time': datetime.now()
        }
        
        # Request settings
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add parallel processing settings
        self.max_concurrent_requests = 1  # Very conservative to avoid rate limits
        self.max_retries = 2  # Reduced retries
        self.retry_delay = 10  # Longer delays
        self.semaphore = None  # Will be initialized in __aenter__
        
        # Category URLs to scrape (reduced to avoid rate limits)
        self.category_urls = [
            '/category/us-immigration-visas/h1b-visa/',
            '/category/us-immigration-visas/',
            '/category/living-in-us/'
        ]
        
        # Enhanced date patterns
        self.date_patterns = [
            # Meta tags
            'meta[property="article:published_time"]',
            'meta[property="article:modified_time"]',
            'meta[name="date"]',
            'meta[name="publishdate"]',
            'meta[name="DC.date.created"]',
            'meta[name="publish-date"]',
            'meta[itemprop="datePublished"]',
            # HTML elements
            'time[datetime]',
            'time[pubdate]',
            '.entry-date',
            '.published',
            '.post-date',
            '.article-date',
            '.meta-date',
            'span[itemprop="datePublished"]',
            # RedBus2US specific
            '.rb-post-date',
            '.post-meta time'
        ]
        
        # URL date patterns
        self.url_date_patterns = [
            r'/(\d{4})/(\d{2})/(\d{2})/',  # /2023/10/15/
            r'/(\d{4})-(\d{2})-(\d{2})',   # /2023-10-15
            r'(\d{4})/(\d{2})/',           # 2023/10/
            r'_(\d{4})(\d{2})(\d{2})',     # _20231015
            r'-(\d{4})(\d{2})(\d{2})',     # -20231015
        ]
    
    async def __aenter__(self):
        """Initialize async resources."""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=self.max_concurrent_requests)
        )
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def retry_request(self, url: str, method: str = 'get', **kwargs):
        """Make a request with retry logic and return response data."""
        for attempt in range(self.max_retries):
            try:
                async with self.semaphore:  # Control concurrent requests
                    if method.lower() == 'get':
                        async with self.session.get(url, **kwargs) as response:
                            if response.status == 200:
                                # Create a simple response-like object with needed methods
                                class ResponseWrapper:
                                    def __init__(self, content, status, headers):
                                        self.content_data = content
                                        self.status = status
                                        self.headers = headers
                                    
                                    async def text(self):
                                        return self.content_data.decode('utf-8', errors='ignore')
                                    
                                    async def read(self):
                                        return self.content_data
                                
                                content = await response.read()
                                return ResponseWrapper(content, response.status, response.headers)
                            elif response.status == 429:  # Too Many Requests
                                retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                                logger.warning(f"Rate limited, waiting {retry_after}s before retry")
                                await asyncio.sleep(retry_after)
                            elif response.status >= 500:  # Server error
                                logger.warning(f"Server error {response.status}, attempt {attempt + 1}/{self.max_retries}")
                                await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                            else:
                                logger.error(f"HTTP {response.status} for {url}")
                                return None
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Request failed for {url}, attempt {attempt + 1}/{self.max_retries}: {e}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {e}")
                return None
        
        logger.error(f"All retries failed for {url}")
        return None
    
    def generate_article_id(self, url: str, published_date: Optional[str] = None) -> str:
        """Generate unique article ID from URL and date."""
        # Extract slug from URL
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p and p != 'index.html']
        slug = path_parts[-1] if path_parts else 'unknown'
        
        # Remove file extensions
        slug = re.sub(r'\.(html|htm|php)$', '', slug)
        
        # Clean slug
        slug = re.sub(r'[^a-zA-Z0-9\-_]', '_', slug)[:50]
        
        # Use published date if available, otherwise current date
        if published_date:
            try:
                date_obj = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                date_str = date_obj.strftime('%Y%m%d')
            except:
                date_str = datetime.now().strftime('%Y%m%d')
        else:
            date_str = datetime.now().strftime('%Y%m%d')
        
        return f"{date_str}_{slug}"
    
    def extract_categories_and_visa_types(self, content: str, url: str) -> Tuple[List[str], List[str]]:
        """Extract categories and visa types from content and URL."""
        content_lower = content.lower()
        url_lower = url.lower()
        
        # Categories based on content themes
        categories = []
        if any(word in content_lower for word in ['fee', 'cost', 'price', 'payment', 'dollar']):
            categories.append('Fees')
        if any(word in content_lower for word in ['document', 'form', 'paper', 'certificate', 'transcript']):
            categories.append('Documents')
        if any(word in content_lower for word in ['interview', 'appointment', 'consulate', 'embassy']):
            categories.append('Interview')
        if any(word in content_lower for word in ['timeline', 'process', 'step', 'procedure', 'how to']):
            categories.append('Process')
        if any(word in content_lower for word in ['policy', 'rule', 'change', 'update', 'new']):
            categories.append('Policy')
        
        # Visa types
        visa_types = []
        visa_patterns = {
            'H1B': ['h1b', 'h-1b'],
            'F1': ['f1', 'f-1', 'student'],
            'H4': ['h4', 'h-4'],
            'L1': ['l1', 'l-1'],
            'B1/B2': ['b1', 'b2', 'b-1', 'b-2', 'tourist', 'visitor'],
            'Green Card': ['green card', 'permanent resident', 'pr'],
            'J1': ['j1', 'j-1', 'exchange'],
            'O1': ['o1', 'o-1', 'extraordinary']
        }
        
        for visa_type, patterns in visa_patterns.items():
            if any(pattern in content_lower or pattern in url_lower for pattern in patterns):
                visa_types.append(visa_type)
        
        # Default categories if none found
        if not categories:
            categories.append('General')
        if not visa_types:
            visa_types.append('General')
        
        return categories, visa_types
    
    async def download_image(self, image_url: str, article_id: str, image_index: int) -> Optional[Dict]:
        """Download an image and return image metadata."""
        if not image_url or not image_url.strip():
            return None
            
        try:
            # Skip data URLs and SVG placeholders
            if image_url.startswith('data:'):
                logger.debug(f"Skipping data URL: {image_url[:100]}...")
                return None
            
            # Skip empty SVG placeholders
            if 'data:image/svg+xml' in image_url and '%3C/svg%3E' in image_url:
                logger.debug(f"Skipping empty SVG placeholder: {image_url[:100]}...")
                return None
            
            # Make sure image URL is absolute
            if image_url.startswith('//'):
                image_url = f"https:{image_url}"
            elif not image_url.startswith(('http://', 'https://')):
                image_url = urljoin(self.base_url, image_url)
                
            # Create article image directory
            article_image_dir = self.images_dir / article_id
            article_image_dir.mkdir(exist_ok=True)
            
            # Get image extension
            parsed_url = urlparse(image_url)
            extension = Path(parsed_url.path).suffix or '.jpg'
            if extension.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
                extension = '.jpg'
            
            # Generate image filename
            image_filename = f"image{image_index:02d}{extension}"
            image_path = article_image_dir / image_filename
            
            # Download image with retry
            response = await self.retry_request(image_url)
            if not response:
                return None
                
            content = await response.read()
            
            # Better image content validation
            is_valid_image = False
            
            # Check for common image headers
            if len(content) > 10:
                # JPEG
                if content.startswith(b'\xff\xd8\xff'):
                    is_valid_image = True
                # PNG
                elif content.startswith(b'\x89PNG\r\n\x1a\n'):
                    is_valid_image = True
                # GIF
                elif content.startswith(b'GIF87a') or content.startswith(b'GIF89a'):
                    is_valid_image = True
                # WebP
                elif b'WEBP' in content[:12]:
                    is_valid_image = True
                # SVG (but not empty ones)
                elif content.startswith(b'<svg') and len(content) > 200:
                    is_valid_image = True
                # Basic size check for other formats
                elif len(content) > 1000 and not content.startswith(b'<!DOCTYPE') and not content.startswith(b'<html'):
                    is_valid_image = True
            
            if is_valid_image:
                async with aiofiles.open(image_path, 'wb') as f:
                    await f.write(content)
                
                # Generate image ID
                image_id = f"{article_id}_img{image_index:02d}"
                
                self.stats['images_downloaded'] += 1
                
                return {
                    'id': image_id,
                    'original_url': image_url,
                    'local_path': str(image_path.relative_to(self.project_root)),
                    'filename': image_filename,
                    'size_bytes': len(content),
                    'downloaded_at': datetime.now().isoformat()
                }
            else:
                logger.debug(f"Skipping invalid image content from {image_url[:100]}... (size: {len(content)} bytes)")
        except Exception as e:
            logger.debug(f"Image download failed for {image_url[:100]}...: {e}")
            self.stats['images_failed'] += 1
        
        return None
    
    async def extract_images_from_content(self, soup: BeautifulSoup, article_id: str, base_url: str) -> List[Dict]:
        """Extract and download all images from article content."""
        images = []
        image_tasks = []
        
        # Find all img tags
        img_tags = soup.find_all('img')
        logger.debug(f"Found {len(img_tags)} img tags in article {article_id}")
        
        for i, img_tag in enumerate(img_tags):
            # Try to get the best image source - prefer data-src, data-lazy-src over src
            src = (img_tag.get('data-src') or 
                  img_tag.get('data-lazy-src') or 
                  img_tag.get('data-original') or 
                  img_tag.get('src'))
            
            if not src:
                continue
            
            # Skip data URLs and empty SVG placeholders immediately
            if (src.startswith('data:') and 
                ('svg+xml' in src and '%3C/svg%3E' in src or len(src) < 100)):
                continue
            
            # Convert relative URLs to absolute
            if src.startswith('//'):
                image_url = f"https:{src}"
            elif src.startswith('/'):
                image_url = urljoin(base_url, src)
            elif not src.startswith(('http', 'data:')):
                image_url = urljoin(base_url, src)
            else:
                image_url = src
            
            # Skip tiny images, icons, placeholders and common non-content images
            skip_keywords = ['icon', 'logo', 'avatar', 'button', 'ad', 'placeholder', 
                           'loading', 'spinner', 'blank', '1x1', 'pixel']
            if any(skip in image_url.lower() for skip in skip_keywords):
                continue
            
            # Skip very small dimensions if specified in URL
            if any(dim in image_url.lower() for dim in ['16x16', '32x32', '50x50', '64x64']):
                continue
            
            # Prepare image metadata
            caption = img_tag.get('alt', '') or img_tag.get('title', '')
            
            # Look for figcaption or nearby text
            parent = img_tag.find_parent(['figure', 'div'])
            if parent:
                figcaption = parent.find('figcaption')
                if figcaption:
                    caption = figcaption.get_text(strip=True) or caption
            
            # Find position in content (simplified)
            position = f"position_{i+1}"
            content_marker = ""
            
            # Try to find surrounding text
            prev_sibling = img_tag.find_previous_sibling(string=True)
            if prev_sibling:
                content_marker = str(prev_sibling).strip()[:100]
            
            # Create task to download image
            task = asyncio.create_task(self.download_image(image_url, article_id, i+1))
            image_tasks.append((task, caption, position, content_marker))
        
        # Process all image downloads in parallel
        for task, caption, position, content_marker in image_tasks:
            try:
                image_data = await task
                if image_data:
                    image_data.update({
                        'caption': caption,
                        'position': position,
                        'content_marker': content_marker
                    })
                    images.append(image_data)
            except Exception as e:
                logger.error(f"Image download task failed: {e}")
        
        return images
    
    async def scrape_article(self, url: str) -> Optional[Dict]:
        """Scrape article with retry logic."""
        try:
            logger.info(f"🔍 Scraping: {url}")
            
            response = await self.retry_request(url)
            if not response:
                return None
            
            html_content = await response.text()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract article data with error handling for each component
            article_data = {
                "article": {
                    "id": self.generate_article_id(url),
                    "url": url,
                    "scraped_at": datetime.now().isoformat(),
                    "title": await self.extract_with_retry(self.extract_title, soup),
                    "published_date": await self.extract_with_retry(self.get_article_date, url),
                    "content": await self.extract_with_retry(self.extract_content, soup),
                    "categories": [],
                    "visa_types": [],
                    "images": []
                }
            }
            
            # Only proceed if we have essential data
            if not article_data["article"]["title"] or not article_data["article"]["content"]:
                logger.error(f"Missing essential data for {url}")
                return None
            
            # Format the published_date if it's a datetime object
            if isinstance(article_data["article"]["published_date"], datetime):
                article_data["article"]["published_date"] = article_data["article"]["published_date"].isoformat()
            elif not article_data["article"]["published_date"]:
                article_data["article"]["published_date"] = datetime.now().isoformat()
            
            # Add categories and visa types
            categories, visa_types = self.extract_categories_and_visa_types(
                article_data["article"]["content"],
                url
            )
            article_data["article"]["categories"] = categories
            article_data["article"]["visa_types"] = visa_types
            
            # Extract and download images in parallel
            article_data["article"]["images"] = await self.extract_images_from_content(soup, article_data["article"]["id"], url)
            
            # Save article to individual JSON file
            article_file = self.articles_dir / f"{article_data['article']['id']}.json"
            async with aiofiles.open(article_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(article_data, indent=2, ensure_ascii=False))
            
            self.stats['articles_scraped'] += 1
            logger.info(f"✅ Saved article: {article_data['article']['id']} ({len(article_data['article']['images'])} images)")
            
            return article_data
            
        except Exception as e:
            logger.error(f"❌ Error scraping {url}: {e}")
            self.stats['articles_failed'] += 1
            return None
    
    def extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article title."""
        # Try various title selectors
        selectors = [
            'h1.entry-title',
            'h1.post-title',
            'h1',
            '.entry-title',
            '.post-title',
            'title'
        ]
        
        for selector in selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 10:
                    return title
        
        return None
    
    def extract_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract main article content."""
        # Remove unwanted elements
        for unwanted in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'sidebar']):
            unwanted.decompose()
        
        # Try various content selectors
        content_selectors = [
            '.entry-content',
            '.post-content',
            '.article-content',
            'article',
            '.content',
            'main'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = content_elem.get_text(separator=' ', strip=True)
                if len(content) > 200:
                    return content
        
        # Fallback: try body content
        body = soup.find('body')
        if body:
            content = body.get_text(separator=' ', strip=True)
            if len(content) > 200:
                return content
        
        return None
    
    async def extract_with_retry(self, func, *args, max_retries: int = 3) -> Any:
        """Execute a function with retry logic."""
        for attempt in range(max_retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args)
                else:
                    result = func(*args)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        return None
    
    def extract_published_date(self, soup: BeautifulSoup, html_content: str) -> Optional[str]:
        """Extract published date from article."""
        # Try all date patterns from self.date_patterns
        for selector in self.date_patterns:
            date_elem = soup.select_one(selector)
            if date_elem:
                date_str = date_elem.get('content') or date_elem.get('datetime') or date_elem.get_text(strip=True)
                if date_str:
                    try:
                        # Try to parse and normalize the date
                        from dateutil import parser
                        parsed_date = parser.parse(date_str)
                        return parsed_date.isoformat()
                    except:
                        continue
        
        # Try to extract from URL
        date_from_url = self.extract_date_from_url(soup.url if hasattr(soup, 'url') else '')
        if date_from_url:
            return date_from_url.isoformat()
        
        # Try text pattern matching
        text_date = self.extract_date_from_text(soup)
        if text_date:
            return text_date.isoformat()
        
        return None
    
    def extract_date_from_text(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract date from article text content."""
        try:
            # Common date formats in text
            date_patterns = [
                r'Published\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
                r'Posted\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
                r'Date\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
                r'Updated\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            ]
            
            # Search in first 1000 characters of text
            text = soup.get_text()[:1000]
            
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        from dateutil import parser
                        from datetime import timezone
                        parsed_date = parser.parse(match.group(1))
                        # Make sure the datetime is timezone-aware
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                        return parsed_date
                    except:
                        continue
            
        except Exception as e:
            logger.debug(f"Error extracting date from text: {e}")
        
        return None
    
    async def get_article_info(self, url: str) -> Optional[Tuple[str, datetime]]:
        """Get article URL and date with enhanced date extraction."""
        try:
            response = await self.retry_request(url)
            if not response:
                return None
            
            html_content = await response.text()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Try all date patterns
            for selector in self.date_patterns:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_str = (date_elem.get('content') or 
                              date_elem.get('datetime') or 
                              date_elem.get_text(strip=True))
                    if date_str:
                        try:
                            from dateutil import parser
                            from datetime import timezone
                            parsed_date = parser.parse(date_str)
                            # Make sure the datetime is timezone-aware
                            if parsed_date.tzinfo is None:
                                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                            return url, parsed_date
                        except:
                            continue
            
            # Try URL patterns
            date_from_url = self.extract_date_from_url(url)
            if date_from_url:
                return url, date_from_url
            
            # Try finding date in text content
            text_date = self.extract_date_from_text(soup)
            if text_date:
                return url, text_date
            
        except Exception as e:
            logger.error(f"Error getting article info for {url}: {e}")
        
        return None
    
    async def process_page(self, page_url: str, min_date: datetime, max_articles: int) -> List[Tuple[str, datetime]]:
        """Process a single page and return article URLs with dates."""
        try:
            response = await self.retry_request(page_url)
            if not response:
                return []
            
            html_content = await response.text()
            urls = await self.extract_urls_from_page(page_url, max_articles)
            
            # Process articles in parallel
            tasks = [self.get_article_info(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter valid results
            articles = []
            for result in results:
                if isinstance(result, Exception):
                    continue
                if result and result[1] and result[1] >= min_date:
                    articles.append(result)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error processing page {page_url}: {e}")
            return []
    
    async def scrape_recent_articles(self, max_articles: int = 1000) -> List[str]:
        """Get recent articles using parallel processing."""
        from datetime import timezone
        two_years_ago = datetime.now(timezone.utc) - timedelta(days=730)
        article_urls_with_dates = []
        
        try:
            # First try the sitemap approach
            sitemap_urls = [
                f"{self.base_url}/sitemap.xml",
                f"{self.base_url}/sitemap_index.xml",
            ]
            
            for sitemap_url in sitemap_urls:
                logger.info(f"🔍 Trying to find articles from: {sitemap_url}")
                response = await self.retry_request(sitemap_url)
                if not response:
                    continue
                
                html_content = await response.text()
                urls = await self.extract_from_sitemap(html_content)
                
                if urls:
                    # Process in parallel with batches to avoid overwhelming
                    batch_size = 10
                    for i in range(0, len(urls), batch_size):
                        batch_urls = urls[i:i+batch_size]
                        tasks = [self.get_article_info(url) for url in batch_urls]
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        for result in results:
                            if isinstance(result, Exception):
                                continue
                            if result and result[1] and result[1] >= two_years_ago:
                                article_urls_with_dates.append(result)
                        
                        # Be nice to the server
                        await asyncio.sleep(8)
                    
                    if article_urls_with_dates:
                        break
            
            # If sitemap didn't work, try category pages
            if not article_urls_with_dates:
                # Gather tasks for all category pages
                category_tasks = []
                for category in self.category_urls:
                    category_url = urljoin(self.base_url, category)
                    for page in range(1, 4):  # Only check first 3 pages to reduce load
                        page_url = f"{category_url}page/{page}/"
                        logger.info(f"🔍 Trying to find articles from: {page_url}")
                        task = self.process_page(page_url, two_years_ago, max_articles)
                        category_tasks.append(task)
                
                # Also try main pages
                main_pages = [
                    f"{self.base_url}/page/1/",
                    f"{self.base_url}/"
                ]
                for page_url in main_pages:
                    logger.info(f"🔍 Trying to find articles from: {page_url}")
                    task = self.process_page(page_url, two_years_ago, max_articles)
                    category_tasks.append(task)
                
                # Process pages sequentially to avoid rate limits
                batch_size = 1  # Process 1 page at a time
                for i in range(0, len(category_tasks), batch_size):
                    batch_tasks = category_tasks[i:i+batch_size]
                    results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Collect results
                    for page_results in results:
                        if isinstance(page_results, Exception):
                            logger.error(f"Page processing failed: {page_results}")
                            continue
                        if page_results:
                            article_urls_with_dates.extend(page_results)
                    
                    # Be nice to the server
                    await asyncio.sleep(8)
            
            # Sort and deduplicate
            seen_urls = set()
            unique_articles = []
            for url, date in sorted(article_urls_with_dates, key=lambda x: x[1], reverse=True):
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_articles.append((url, date))
            
            # Return top N articles
            return [url for url, _ in unique_articles[:max_articles]]
            
        except Exception as e:
            logger.error(f"Error in scrape_recent_articles: {e}")
            return []
    
    async def extract_urls_from_page(self, page_url: str, max_urls: int = 100) -> List[str]:
        """Extract article URLs from a given page."""
        urls = set()
        
        try:
            response = await self.retry_request(page_url)
            if not response:
                return list(urls)
            
            html_content = await response.text()
            
            # Handle sitemap
            if 'sitemap' in page_url.lower() and ('xml' in html_content or '<loc>' in html_content):
                return await self.extract_from_sitemap(html_content)
            
            # Handle regular pages
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find article links with various selectors
            link_selectors = [
                'a[href*="redbus2us.com"]',
                'a[href^="/"]',
                '.entry-title a',
                '.post-title a',
                'h1 a', 'h2 a', 'h3 a',
                'article a',
            ]
            
            for selector in link_selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href and self.is_article_url(href):
                        if href.startswith('/'):
                            href = urljoin(self.base_url, href)
                        elif not href.startswith('http'):
                            href = urljoin(page_url, href)
                        urls.add(href)
                        
                        if len(urls) >= max_urls:
                            break
                
                if len(urls) >= max_urls:
                    break
            
        except Exception as e:
            logger.error(f"❌ Error extracting URLs from {page_url}: {e}")
        
        return list(urls)
    
    async def extract_from_sitemap(self, xml_content: str) -> List[str]:
        """Extract URLs from sitemap XML."""
        urls = []
        
        try:
            # Parse XML content
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(xml_content, 'xml')
            
            # Find all loc tags
            loc_tags = soup.find_all('loc')
            
            for loc in loc_tags:
                url = loc.get_text().strip()
                if self.is_article_url(url):
                    urls.append(url)
            
            logger.info(f"📍 Extracted {len(urls)} URLs from sitemap")
            
        except Exception as e:
            logger.error(f"❌ Error parsing sitemap: {e}")
        
        return urls
    
    async def get_article_date(self, url: str) -> Optional[datetime]:
        """Get the published date of an article without downloading full content."""
        try:
            # Get article page with retry
            response = await self.retry_request(url)
            if not response:
                return None
            
            # Read content
            html_content = await response.text()
            # Use first part only for efficiency
            partial_content = html_content[:8192]  # First 8KB chars
            soup = BeautifulSoup(partial_content, 'html.parser')
            
            # Try to find date with enhanced patterns
            for selector in self.date_patterns:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_str = (date_elem.get('content') or 
                              date_elem.get('datetime') or 
                              date_elem.get_text(strip=True))
                    if date_str:
                        try:
                            from dateutil import parser
                            from datetime import timezone
                            parsed_date = parser.parse(date_str)
                            # Make sure the datetime is timezone-aware
                            if parsed_date.tzinfo is None:
                                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                            return parsed_date
                        except:
                            continue
            
            # Try to extract from URL
            date_from_url = self.extract_date_from_url(url)
            if date_from_url:
                return date_from_url
            
            # Try text pattern matching
            text_date = self.extract_date_from_text(soup)
            if text_date:
                return text_date
            
        except Exception as e:
            logger.debug(f"Could not get date for {url}: {e}")
        
        return None
    
    def extract_date_from_url(self, url: str) -> Optional[datetime]:
        """Try to extract date from URL pattern."""
        # Use patterns from self.url_date_patterns
        for pattern in self.url_date_patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    if len(match.groups()) == 3:
                        year, month, day = match.groups()
                        from datetime import timezone
                        return datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
                    elif len(match.groups()) == 2:
                        year, month = match.groups()
                        from datetime import timezone
                        return datetime(int(year), int(month), 1, tzinfo=timezone.utc)
                except:
                    continue
        
        return None
    
    async def scrape_category_urls(self, category_url: str, max_articles: int = 50) -> List[str]:
        """Get article URLs from a category page."""
        return await self.extract_urls_from_page(category_url, max_articles)
    
    def is_article_url(self, url: str) -> bool:
        """Check if URL looks like an article."""
        if not url:
            return False
        
        # Skip certain patterns
        skip_patterns = [
            'wp-admin', 'wp-content', 'feed', 'rss', 'xml',
            'category', 'tag', 'author', 'page',
            '.jpg', '.png', '.gif', '.pdf', '.zip',
            'facebook.com', 'twitter.com', 'linkedin.com',
            'mailto:', 'tel:', '#'
        ]
        
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in skip_patterns):
            return False
        
        # Must look like an article
        if len(url) < 30:  # Too short
            return False
        
        # Should have meaningful path
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        if len(path_parts) < 1:
            return False
        
        return True
    
    def print_stats(self):
        """Print scraping statistics."""
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        
        print("\n" + "="*60)
        print("📊 SCRAPING STATISTICS")
        print("="*60)
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📄 Articles scraped: {self.stats['articles_scraped']}")
        print(f"❌ Articles failed: {self.stats['articles_failed']}")
        print(f"🖼️  Images downloaded: {self.stats['images_downloaded']}")
        print(f"❌ Images failed: {self.stats['images_failed']}")
        print(f"📁 Output directory: {self.articles_dir}")
        print("="*60)

async def main(max_articles: int = 100):
    """Main scraping function - downloads recent articles ordered by date (newest first)."""
    async with SimplifiedRedBusScraper() as scraper:
        logger.info(f"🚀 Starting simplified RedBus2US scraper for last 2 years (max {max_articles} articles)...")
        
        # Get recent articles ordered by published date (newest first)
        recent_urls = await scraper.scrape_recent_articles(max_articles=max_articles)
        
        if not recent_urls:
            logger.error("❌ No recent articles found")
            return
        
        logger.info(f"📋 Found {len(recent_urls)} recent articles to scrape")
        
        # Scrape articles sequentially to avoid rate limits
        for i, url in enumerate(recent_urls, 1):
            logger.info(f"📄 Processing article {i}/{len(recent_urls)}: {url}")
            await scraper.scrape_article(url)
            
            # Be nice to the server - longer delays
            if i < len(recent_urls):
                await asyncio.sleep(5)
        
        scraper.print_stats()

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    max_articles = 100  # default
    if len(sys.argv) > 1:
        try:
            max_articles = int(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid max_articles value: {sys.argv[1]}. Using default: 100")
    
    logger.info(f"Starting scraper with max_articles={max_articles}")
    asyncio.run(main(max_articles))
