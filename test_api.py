#!/usr/bin/env python3
"""
Simplified FastAPI app for testing.
"""

from fastapi import FastAPI, File, Form, UploadFile
import uvicorn

# Create FastAPI application
app = FastAPI(
    title="Test API",
    description="Test API for debugging",
    version="1.0.0",
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Test API is running"}

@app.get("/hello")
async def hello():
    return {"message": "Hello World"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    return {
        "filename": file.filename,
        "content_type": file.content_type,
    }

if __name__ == "__main__":
    uvicorn.run("test_api:app", host="0.0.0.0", port=8001, reload=True)