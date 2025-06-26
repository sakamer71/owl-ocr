"""
Security middleware for API protection.

Implements rate limiting and security headers.
"""

import os
import time
from typing import Callable, Dict

from fastapi import FastAPI, Request, Response
try:
    from starlette.middleware.base import BaseHTTPMiddleware
except ImportError:
    from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse


# Rate limiting configuration
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # in seconds
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "100"))  # per window

# Simple in-memory store for rate limiting
# In production, this should use Redis or another distributed cache
rate_limit_store: Dict[str, Dict[str, int]] = {}


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for implementing security features."""
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request through security middleware.
        
        Args:
            request: Incoming request
            call_next: Next middleware or endpoint
            
        Returns:
            Response with security headers and rate limiting
        """
        # Check rate limit if enabled
        if RATE_LIMIT_ENABLED and request.method != "OPTIONS":
            client_ip = request.client.host if request.client else "unknown"
            
            # Check if client is rate limited
            if self._is_rate_limited(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
                )
            
            # Update rate limit counter
            self._update_rate_limit(client_ip)
        
        # Process the request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
    
    def _is_rate_limited(self, client_ip: str) -> bool:
        """
        Check if client is rate limited.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if client is rate limited, False otherwise
        """
        now = int(time.time())
        window_start = now - RATE_LIMIT_WINDOW
        
        if client_ip in rate_limit_store:
            # Clean up old requests
            rate_limit_store[client_ip] = {
                ts: count for ts, count in rate_limit_store[client_ip].items() 
                if int(ts) > window_start
            }
            
            # Count requests in current window
            total_requests = sum(rate_limit_store[client_ip].values())
            
            # Check if limit is exceeded
            if total_requests >= RATE_LIMIT_MAX_REQUESTS:
                return True
        
        return False
    
    def _update_rate_limit(self, client_ip: str) -> None:
        """
        Update rate limit counters for client.
        
        Args:
            client_ip: Client IP address
        """
        now = str(int(time.time()))
        
        if client_ip not in rate_limit_store:
            rate_limit_store[client_ip] = {}
        
        if now not in rate_limit_store[client_ip]:
            rate_limit_store[client_ip][now] = 0
        
        rate_limit_store[client_ip][now] += 1


def add_security_middleware(app: FastAPI) -> None:
    """
    Add security middleware to FastAPI app.
    
    Args:
        app: FastAPI application
    """
    app.add_middleware(SecurityMiddleware)