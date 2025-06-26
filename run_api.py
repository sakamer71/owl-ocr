#!/usr/bin/env python3
"""
Run script for the Owl OCR FastAPI server.

This script starts the FastAPI server using uvicorn.
"""

import os
import uvicorn

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    # Log configuration
    print(f"Starting Owl OCR API server at http://{host}:{port}")
    print("Press Ctrl+C to stop the server")
    
    # Start server
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=True,  # Enable auto-reload during development
        workers=4,    # Number of worker processes
        log_level="info"
    )