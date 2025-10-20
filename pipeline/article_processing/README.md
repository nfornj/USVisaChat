# RedBus2US Article Scraper

## Overview

The enhanced RedBus2US scraper downloads articles ordered by published date (newest first) from the last 2 years, with clean JSON structure and automatic image handling.

## Key Features

### ✅ **Date-Ordered Scraping**
- **Downloads articles in descending order by published date** (latest first → older)
- **Filters to last 2 years only** (730 days from current date)
- **Smart date extraction** from meta tags, URL patterns, and content

### ✅ **Multiple Discovery Methods**
- **Sitemap parsing** - Primary method for discovering articles
- **Homepage crawling** - Fallback method
- **Category page parsing** - Additional discovery
- **URL pattern detection** - Identifies valid article URLs

### ✅ **Clean Data Structure**
```json
{
  "article": {
    "id": "20241012_article-slug",
    "url": "https://redbus2us.com/article-url/",
    "scraped_at": "2024-10-12T10:30:00",
    "title": "Article Title",
    "published_date": "2024-10-12T09:00:00",
    "content": "Full article text...",
    "categories": ["H1B Visa", "Process", "Documents"],
    "visa_types": ["H1B", "Green Card"],
    "images": [...]
  }
}
```

## Usage

### **Basic Usage**
```bash
# Scrape 100 most recent articles (default)
uv run python pipeline/article_processing/simplified_redbus_scraper.py

# Scrape specific number of articles
uv run python pipeline/article_processing/simplified_redbus_scraper.py 250

# Scrape maximum articles (up to 1000)
uv run python pipeline/article_processing/simplified_redbus_scraper.py 1000
```

### **Programmatic Usage**
```python
import asyncio
from simplified_redbus_scraper import SimplifiedRedBusScraper

async def scrape_articles():
    async with SimplifiedRedBusScraper() as scraper:
        # Get recent URLs ordered by date (newest first)
        recent_urls = await scraper.scrape_recent_articles(max_articles=100)
        
        # Scrape each article
        for url in recent_urls:
            article_data = await scraper.scrape_article(url)
            print(f"Scraped: {article_data['article']['title']}")

asyncio.run(scrape_articles())
```

### **Test the Date Ordering**
```bash
# Run test to verify date-ordered functionality
uv run python pipeline/article_processing/test_date_scraping.py
```

## Date Ordering Implementation

### **How It Works**

1. **Discovery Phase**
   ```python
   # Try multiple sources for article URLs
   urls_to_try = [
       f"{base_url}/sitemap.xml",        # Primary - structured data
       f"{base_url}/sitemap_index.xml",  # Alternative sitemap
       f"{base_url}/page/1/",            # Recent posts page
       f"{base_url}/",                   # Homepage
   ]
   ```

2. **Date Extraction Phase**
   ```python
   # For each discovered URL, extract published date
   article_date = await scraper.get_article_date(url)
   
   # Methods used (in order):
   # 1. Meta tags: article:published_time, publishdate, etc.
   # 2. Structured data: <time datetime="...">
   # 3. URL patterns: /2024/10/12/ or /2024-10-12
   ```

3. **Filtering Phase**
   ```python
   two_years_ago = datetime.now() - timedelta(days=730)
   if article_date >= two_years_ago:
       article_urls_with_dates.append((url, article_date))
   ```

4. **Sorting Phase**
   ```python
   # Sort by date in descending order (newest first)
   article_urls_with_dates.sort(key=lambda x: x[1], reverse=True)
   ```

### **Date Extraction Methods**

The scraper uses multiple methods to find article dates:

1. **Meta Tags (Most Reliable)**
   - `<meta property="article:published_time" content="2024-10-12T10:00:00Z">`
   - `<meta name="date" content="2024-10-12">`
   - `<meta name="publishdate" content="2024-10-12">`

2. **Structured HTML**
   - `<time datetime="2024-10-12T10:00:00Z">October 12, 2024</time>`

3. **URL Patterns**
   - `/2024/10/12/article-title/`
   - `/2024-10-12-article-title/`
   - `/2024/10/article-title/`

## Output Structure

### **File Organization**
```
data/redbus2us_raw/
├── articles/
│   ├── 20241012_h1b-lottery-results.json
│   ├── 20241011_visa-policy-update.json
│   └── ...
└── images/
    ├── 20241012_h1b-lottery-results/
    │   ├── image01.jpg
    │   └── image02.png
    └── ...
```

### **Article JSON Structure**
```json
{
  "article": {
    "id": "20241012_h1b-lottery-results",
    "url": "https://redbus2us.com/h1b-lottery-results/",
    "scraped_at": "2024-10-12T15:30:45",
    "title": "H1B Lottery Results for 2025",
    "published_date": "2024-10-12T10:00:00",
    "content": "Complete article text content...",
    "categories": ["H1B Visa", "Process", "Policy"],
    "visa_types": ["H1B"],
    "images": [
      {
        "id": "20241012_h1b-lottery-results_img01",
        "original_url": "https://redbus2us.com/wp-content/uploads/image.jpg",
        "local_path": "data/redbus2us_raw/images/20241012_h1b-lottery-results/image01.jpg",
        "filename": "image01.jpg",
        "size_bytes": 156789,
        "downloaded_at": "2024-10-12T15:31:02",
        "caption": "H1B lottery statistics chart",
        "position": "position_1",
        "content_marker": "The following chart shows..."
      }
    ]
  }
}
```

## Configuration

### **Default Settings**
- **Max articles:** 100 (can be overridden)
- **Date range:** Last 2 years (730 days)
- **Request delay:** 2 seconds between articles
- **Timeout:** 30 seconds per request
- **Concurrent limit:** 5 connections per host

### **Customization**
```python
# Modify the scraper settings
scraper = SimplifiedRedBusScraper()

# Change date range (e.g., last 1 year)
one_year_ago = datetime.now() - timedelta(days=365)

# Adjust request delays
await asyncio.sleep(5)  # 5 second delay instead of 2
```

## Performance

### **Expected Performance**
- **Discovery:** 10-30 seconds to find article URLs
- **Date extraction:** 1-2 seconds per article (efficient HEAD requests)
- **Full scraping:** 3-5 seconds per article (including images)
- **Total time for 100 articles:** ~10-15 minutes

### **Optimization Features**
- **Efficient date checking:** Uses HEAD requests when possible
- **Partial content reading:** Only reads first 8KB to find dates
- **Connection pooling:** Reuses HTTP connections
- **Smart filtering:** Skips non-article URLs early

## Error Handling

The scraper includes comprehensive error handling:

- **Network errors:** Automatic retries and graceful failures
- **Invalid dates:** Multiple parsing methods with fallbacks
- **Missing content:** Skips articles with insufficient content
- **Image failures:** Continues scraping even if images fail
- **Rate limiting:** Built-in delays to respect server resources

## Verification

To verify the date ordering is working correctly:

1. **Run the test script:**
   ```bash
   uv run python pipeline/article_processing/test_date_scraping.py
   ```

2. **Check the output logs:**
   - Look for "✅ Articles are correctly ordered by date (newest first)"
   - Verify date range shows recent articles only
   - Confirm all articles are within last 2 years

3. **Manual verification:**
   ```bash
   # Check first few scraped articles
   ls -la data/redbus2us_raw/articles/ | head -10
   
   # The filenames should show recent dates first (20241012_, 20241011_, etc.)
   ```

## Troubleshooting

### **Common Issues**

1. **No articles found:**
   - Check internet connection
   - Verify RedBus2US website is accessible
   - Try running the test script first

2. **Date ordering seems wrong:**
   - Run the test script to verify
   - Check if RedBus2US changed their date format
   - Look at the logs for date extraction warnings

3. **Missing dependencies:**
   ```bash
   cd backend
   uv add aiohttp aiofiles beautifulsoup4 python-dateutil
   ```

### **Debug Mode**
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show detailed date extraction attempts
```

## Integration

This scraper integrates with the larger pipeline:

```bash
# 1. Scrape recent articles (date-ordered)
uv run python pipeline/article_processing/simplified_redbus_scraper.py 200

# 2. Organize articles (optional - already organized by date)
uv run python pipeline/article_processing/organize_articles.py

# 3. Summarize articles  
uv run python pipeline/article_processing/article_summarizer.py

# 4. Generate vectors for database
uv run python backend/scripts/generate_article_vectors.py
```