"""
Security Middleware for Production
Implements rate limiting, security headers, input validation, and request size limits
"""

import re
import logging
from typing import Callable
from collections import defaultdict
from time import time
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    - Content Security Policy (CSP)
    - X-Frame-Options
    - X-Content-Type-Options
    - Strict-Transport-Security (HSTS)
    - X-XSS-Protection
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Content Security Policy - Prevents XSS attacks
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable browser XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # HSTS - Force HTTPS (only in production with HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiter using sliding window algorithm
    - Per-IP rate limiting
    - Configurable limits per endpoint pattern
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Store request timestamps per IP: {ip: {endpoint: deque of timestamps}}
        self.requests = defaultdict(lambda: defaultdict(list))
        
        # Rate limits: {endpoint_pattern: (max_requests, window_seconds)}
        self.limits = {
            "/auth/request-code": (5, 60),  # 5 codes per minute
            "/auth/verify-code": (10, 60),  # 10 verifications per minute
            "/chat/upload-image": (10, 60),  # 10 uploads per minute
            "/api/ai-news": (20, 60),  # 20 news requests per minute
            "/search": (30, 60),  # 30 searches per minute
            "default": (60, 60),  # 60 requests per minute for other endpoints
        }
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for proxy headers (X-Forwarded-For, X-Real-IP)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def get_limit(self, path: str) -> tuple:
        """Get rate limit for endpoint"""
        for pattern, limit in self.limits.items():
            if pattern in path:
                return limit
        return self.limits["default"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/docs", "/openapi.json"] or \
           request.url.path.startswith(("/assets", "/media")):
            return await call_next(request)
        
        client_ip = self.get_client_ip(request)
        endpoint = request.url.path
        now = time()
        
        max_requests, window = self.get_limit(endpoint)
        
        # Get request history for this IP and endpoint
        request_history = self.requests[client_ip][endpoint]
        
        # Remove old timestamps outside the window
        request_history[:] = [ts for ts in request_history if now - ts < window]
        
        # Check if rate limit exceeded
        if len(request_history) >= max_requests:
            logger.warning(f"⚠️ Rate limit exceeded for {client_ip} on {endpoint}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Max {max_requests} requests per {window} seconds.",
                    "retry_after": window
                },
                headers={"Retry-After": str(window)}
            )
        
        # Record this request
        request_history.append(now)
        
        # Clean up old IPs periodically (simple cleanup every 1000 requests)
        if len(self.requests) > 1000:
            self._cleanup_old_entries(now)
        
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max_requests - len(request_history)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + window))
        
        return response
    
    def _cleanup_old_entries(self, current_time: float):
        """Cleanup old IP entries"""
        max_window = max(limit[1] for limit in self.limits.values())
        ips_to_remove = []
        
        for ip, endpoints in self.requests.items():
            # Remove endpoints with no recent activity
            endpoints_to_remove = []
            for endpoint, history in endpoints.items():
                history[:] = [ts for ts in history if current_time - ts < max_window * 2]
                if not history:
                    endpoints_to_remove.append(endpoint)
            
            for endpoint in endpoints_to_remove:
                del endpoints[endpoint]
            
            if not endpoints:
                ips_to_remove.append(ip)
        
        for ip in ips_to_remove:
            del self.requests[ip]


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Limit request body size to prevent memory exhaustion attacks
    """
    
    def __init__(self, app: ASGIApp, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check Content-Length header
        content_length = request.headers.get("Content-Length")
        
        if content_length:
            if int(content_length) > self.max_size:
                logger.warning(f"⚠️ Request too large: {content_length} bytes from {request.client.host if request.client else 'unknown'}")
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": f"Request body too large. Max size: {self.max_size} bytes"}
                )
        
        return await call_next(request)


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Basic input validation to prevent common attacks
    - SQL injection patterns
    - NoSQL injection patterns
    - XSS patterns
    """
    
    # Suspicious patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(--|\#|\/\*)",
    ]
    
    NOSQL_INJECTION_PATTERNS = [
        r"(\$gt|\$lt|\$ne|\$eq)",
        r"(\$where|\$regex)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip validation for GET requests without query params
        if request.method == "GET" and not request.query_params:
            return await call_next(request)
        
        # Validate query parameters
        for key, value in request.query_params.items():
            if self._is_suspicious(value):
                logger.warning(f"⚠️ Suspicious input detected in query param '{key}': {value[:100]}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid input detected"}
                )
        
        # For POST/PUT requests, we'd need to read body (impacts performance)
        # Better to validate in Pydantic models
        
        return await call_next(request)
    
    def _is_suspicious(self, value: str) -> bool:
        """Check if input contains suspicious patterns"""
        value_lower = value.lower()
        
        # Check SQL injection
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        # Check NoSQL injection
        for pattern in self.NOSQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        # Check XSS
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False


def sanitize_string(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input string
    - Remove potential XSS
    - Limit length
    - Normalize whitespace
    """
    if not text:
        return ""
    
    # Limit length
    text = text[:max_length]
    
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove potential script tags (basic XSS prevention)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove javascript: protocol
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    # Remove event handlers
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    
    return text


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) and len(email) <= 254


def validate_display_name(name: str) -> bool:
    """Validate display name"""
    if not name or len(name) < 2 or len(name) > 50:
        return False
    
    # Only allow alphanumeric, spaces, and basic punctuation
    pattern = r'^[a-zA-Z0-9\s\-_.]+$'
    return bool(re.match(pattern, name))
