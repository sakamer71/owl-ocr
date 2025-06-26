#!/usr/bin/env python3
"""
Improved entry point for Owl OCR FastAPI server.

This script ensures proper module imports and starts the FastAPI server.
"""

import os
import sys
from pathlib import Path

# Add the project root directory to Python path
root_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(root_dir))

# Set environment variable for Python module loading
os.environ["PYTHONPATH"] = f"{root_dir}:{os.environ.get('PYTHONPATH', '')}"

# Now import and run uvicorn
import uvicorn

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    # Log configuration
    print(f"Starting Owl OCR API server at http://{host}:{port}")
    print(f"API documentation available at http://{host}:{port}/docs")
    print("Press Ctrl+C to stop the server")
    
    # Start server
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=[str(root_dir)],  # Watch only our project directory
        log_level="info"
    )