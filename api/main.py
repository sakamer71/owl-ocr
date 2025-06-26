#!/usr/bin/env python3
"""
FastAPI application for Owl OCR service.

This module serves as the entry point for the FastAPI application,
setting up the API routes and middleware for the OCR service.
"""

import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import security middleware
try:
    from api.middleware.security import add_security_middleware
except ImportError:
    from middleware.security import add_security_middleware

# Import routers
try:
    from api.routers import process, jobs
except ImportError:
    # When running directly
    from routers import process, jobs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Owl OCR API",
    description="API for OCR and text extraction from various document formats",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security middleware
add_security_middleware(app)

# Create global exception handler for all exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An error occurred processing the request", "detail": str(exc)},
    )

# Include routers
app.include_router(process.router, prefix="/api", tags=["Process"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])

# Root endpoint for API health check
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Owl OCR API is running"}

@app.get("/api/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "Service is healthy"}

if __name__ == "__main__":
    # For local development - not used in production with proper ASGI server
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True)