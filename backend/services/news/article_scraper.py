"""
Article Scraper
Fetches full article content from URLs for comprehensive AI summarization
"""

import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional
import time

logger = logging.getLogger(__name__)


def scrape_article_content(url: str, timeout: int = 10) -> Optional[str]:
    """
    Scrape full article content from a URL
    
    Args:
        url: Article URL to scrape
        timeout: Request timeout in seconds
        
    Returns:
        Full article text or None if scraping failed
    """
    try:
        # Set user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        logger.info(f"🌐 Scraping article from: {url}")
        
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script, style, nav, footer elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
            element.decompose()
        
        # Try common article content selectors (in order of preference)
        article_selectors = [
            'article',
            '[role="article"]',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.content',
            'main',
            '[itemprop="articleBody"]',
            '.story-body',
            '#article-body'
        ]
        
        article_text = None
        
        # Try each selector
        for selector in article_selectors:
            elements = soup.select(selector)
            if elements:
                article_element = elements[0]
                
                # Extract text from paragraphs
                paragraphs = article_element.find_all(['p', 'h1', 'h2', 'h3', 'h4'])
                if paragraphs:
                    article_text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                    if len(article_text) > 200:  # Minimum viable content length
                        logger.info(f"✅ Extracted {len(article_text)} chars using selector: {selector}")
                        break
        
        # Fallback: Get all paragraph text if specific selectors didn't work
        if not article_text or len(article_text) < 200:
            paragraphs = soup.find_all('p')
            article_text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50])
            if article_text:
                logger.info(f"✅ Extracted {len(article_text)} chars using fallback paragraph extraction")
        
        # Clean up the text
        if article_text:
            # Remove excessive whitespace
            article_text = ' '.join(article_text.split())
            # Limit to reasonable size (don't send massive articles to Groq)
            max_length = 8000  # ~8000 chars = ~2000 tokens
            if len(article_text) > max_length:
                article_text = article_text[:max_length] + "..."
                logger.info(f"✂️ Truncated article to {max_length} chars")
            
            return article_text
        
        logger.warning(f"⚠️ Could not extract article content from {url}")
        return None
        
    except requests.Timeout:
        logger.error(f"⏱️ Timeout scraping {url}")
        return None
    except requests.RequestException as e:
        logger.error(f"❌ Request error scraping {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error scraping {url}: {e}")
        return None


def scrape_with_fallback(url: str, fallback_content: str, max_retries: int = 2) -> str:
    """
    Try to scrape article with fallback to original content
    
    Args:
        url: Article URL
        fallback_content: Original content/snippet to use if scraping fails
        max_retries: Number of retry attempts
        
    Returns:
        Scraped content or fallback content
    """
    for attempt in range(max_retries):
        scraped = scrape_article_content(url, timeout=10)
        if scraped:
            return scraped
        
        if attempt < max_retries - 1:
            logger.info(f"🔄 Retry {attempt + 1}/{max_retries} for {url}")
            time.sleep(1)  # Brief delay before retry
    
    logger.warning(f"⚠️ Scraping failed after {max_retries} attempts, using fallback content")
    return fallback_content
