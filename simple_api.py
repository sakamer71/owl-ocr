#!/usr/bin/env python3
"""
Simplified API without middleware for testing.
"""

import logging
import os
from fastapi import FastAPI, File, UploadFile, Form
from typing import Optional
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application - no middleware
app = FastAPI(
    title="Owl OCR API (Simple)",
    description="Simplified API for OCR and text extraction",
    version="1.0.0",
)

# Basic routes for testing
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Simplified Owl OCR API is running"}

@app.get("/api/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "Service is healthy"}

@app.post("/api/process", tags=["Process"])
async def process_file(file: UploadFile = File(...)):
    """Simple file upload endpoint for testing."""
    return {
        "status": "accepted",
        "file_name": file.filename,
        "content_type": file.content_type,
        "job_id": "test-job-123"
    }

@app.get("/api/jobs/{job_id}", tags=["Jobs"])
async def get_job_status(job_id: str):
    """Simple job status endpoint for testing."""
    return {
        "job_id": job_id,
        "status": "completed",
        "file_name": "test.pdf",
        "file_type": "pdf",
        "created_at": "2025-06-26T10:00:00",
        "updated_at": "2025-06-26T10:01:00",
        "progress": 100
    }

if __name__ == "__main__":
    # For local development
    port = int(os.getenv("PORT", "8000"))
    host = "0.0.0.0"
    print(f"Starting simplified API server at http://{host}:{port}")
    print(f"API documentation available at http://{host}:{port}/docs")
    uvicorn.run("simple_api:app", host=host, port=port, reload=True)