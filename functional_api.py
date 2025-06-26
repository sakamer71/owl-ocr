#!/usr/bin/env python3
"""
Functional API with actual OCR processing.
"""

import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
import uvicorn

# Import the actual OCR processing functions
from src.utils.parse_image import extract_image_text
from src.utils.parse_pdf import extract_pdf_text_tables_images
from src.utils.parse_pptx import extract_pptx_text_tables_images

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Owl OCR API (Functional)",
    description="API for OCR and text extraction from various document formats",
    version="1.0.0",
)

# Simple in-memory job storage
jobs = {}
job_results = {}

# Directory for uploads
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Utility function to determine file type
def get_file_type(file_path):
    """Determine file type based on file extension."""
    path = Path(file_path)
    ext = path.suffix.lower()
    
    file_type_map = {
        '.pptx': 'pptx',
        '.ppt': 'pptx',
        '.png': 'image',
        '.jpeg': 'image',
        '.jpg': 'image',
        '.pdf': 'pdf',
    }
    
    return file_type_map.get(ext)

async def save_upload_file(upload_file: UploadFile) -> str:
    """Save an uploaded file to disk."""
    # Create unique filename to avoid collisions
    file_id = uuid.uuid4().hex
    filename = f"{file_id}_{upload_file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save file to disk
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)
        return file_path
    except Exception as e:
        logger.error(f"Error saving file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    finally:
        upload_file.file.close()

async def process_file_background(
    job_id: str, 
    file_path: str, 
    file_type: str
):
    """Process a file in the background."""
    try:
        # Update job status
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 20
        
        # Create output directory
        output_dir = os.path.join("parsed_docs", job_id)
        os.makedirs(output_dir, exist_ok=True)
        
        result = {
            "job_id": job_id,
            "file_name": os.path.basename(file_path),
            "file_type": file_type,
            "texts": [],
            "tables": [],
            "images": [],
            "output_files": {},
        }
        
        # Process based on file type
        if file_type == "image":
            # Update status
            jobs[job_id]["progress"] = 40
            
            # Extract text from image
            extracted_text = extract_image_text(file_path)
            
            # Save text to file
            base_name = Path(file_path).stem
            out_text = os.path.join(output_dir, f"{base_name}.txt")
            
            with open(out_text, "w", encoding="utf-8") as f:
                f.write(extracted_text)
            
            # Add result
            result["texts"].append({
                "text": extracted_text,
                "source": "image",
                "page_number": None
            })
            result["output_files"] = {"text": out_text}
            
        elif file_type == "pdf":
            # Update status
            jobs[job_id]["progress"] = 40
            
            # Create images directory
            base_name = Path(file_path).stem
            images_dir = os.path.join(output_dir, base_name)
            os.makedirs(images_dir, exist_ok=True)
            
            # Extract PDF content
            texts, tables_html = extract_pdf_text_tables_images(file_path, images_dir=images_dir)
            
            # Save text and tables
            out_text = os.path.join(output_dir, f"{base_name}.txt")
            out_tables = os.path.join(output_dir, f"{base_name}_tables.html")
            
            with open(out_text, "w", encoding="utf-8") as f:
                for t in texts:
                    f.write(t.strip() + "\n\n")
                    
            with open(out_tables, "w", encoding="utf-8") as f:
                for html in tables_html:
                    f.write(html + "\n\n")
            
            # Add results
            for text in texts:
                result["texts"].append({
                    "text": text,
                    "source": "pdf",
                    "page_number": None
                })
            
            for html in tables_html:
                result["tables"].append({
                    "html": html,
                    "source": "pdf",
                    "page_number": None
                })
            
            # Add image files
            if os.path.exists(images_dir):
                for img_file in os.listdir(images_dir):
                    if img_file.startswith("page_") and img_file.endswith(".png"):
                        try:
                            page_num = int(img_file.replace("page_", "").replace(".png", ""))
                            result["images"].append({
                                "path": os.path.join(images_dir, img_file),
                                "source": "page",
                                "page_number": page_num
                            })
                        except ValueError:
                            result["images"].append({
                                "path": os.path.join(images_dir, img_file),
                                "source": "page",
                                "page_number": None
                            })
            
            result["output_files"] = {
                "text": out_text,
                "tables": out_tables,
                "images_dir": images_dir
            }
            
        elif file_type == "pptx":
            # Update status
            jobs[job_id]["progress"] = 40
            
            # Create images directory
            base_name = Path(file_path).stem
            images_dir = os.path.join(output_dir, base_name)
            os.makedirs(images_dir, exist_ok=True)
            
            # Extract PPTX content
            texts, tables_html = extract_pptx_text_tables_images(file_path, images_dir=images_dir)
            
            # Save text and tables
            out_text = os.path.join(output_dir, f"{base_name}.txt")
            out_tables = os.path.join(output_dir, f"{base_name}_tables.html")
            
            with open(out_text, "w", encoding="utf-8") as f:
                for t in texts:
                    f.write(t.strip() + "\n\n")
                    
            with open(out_tables, "w", encoding="utf-8") as f:
                for html in tables_html:
                    f.write(html + "\n\n")
            
            # Add results
            for text in texts:
                result["texts"].append({
                    "text": text,
                    "source": "slide",
                    "page_number": None
                })
            
            for html in tables_html:
                result["tables"].append({
                    "html": html,
                    "source": "slide",
                    "page_number": None
                })
            
            # Add image files
            if os.path.exists(images_dir):
                for img_file in os.listdir(images_dir):
                    if img_file.startswith("slide") and "_img" in img_file:
                        try:
                            slide_part = img_file.split("_")[0]
                            slide_num = int(slide_part.replace("slide", ""))
                            result["images"].append({
                                "path": os.path.join(images_dir, img_file),
                                "source": "slide",
                                "page_number": slide_num
                            })
                        except ValueError:
                            result["images"].append({
                                "path": os.path.join(images_dir, img_file),
                                "source": "slide",
                                "page_number": None
                            })
            
            result["output_files"] = {
                "text": out_text,
                "tables": out_tables,
                "images_dir": images_dir
            }
        
        # Update job status to completed and store result
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        job_results[job_id] = result
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
        # Update job status to failed
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Processing failed: {str(e)}"

# API routes
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Owl OCR API is running"}

@app.get("/api/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "Service is healthy"}

@app.post("/api/process", tags=["Process"])
async def process_file_auto(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Process a file with automatic format detection."""
    try:
        # Save uploaded file
        file_path = await save_upload_file(file)
        
        # Detect file type
        file_type = get_file_type(file_path)
        if not file_type:
            os.remove(file_path)  # Clean up
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {Path(file.filename).suffix}"
            )
        
        # Create job
        job_id = uuid.uuid4().hex
        job_data = {
            "job_id": job_id,
            "file_name": file.filename,
            "file_type": file_type,
            "status": "pending",
            "created_at": str(uuid.uuid1().time),
            "updated_at": str(uuid.uuid1().time),
            "progress": 0,
        }
        jobs[job_id] = job_data
        
        # Start background processing
        background_tasks.add_task(
            process_file_background,
            job_id,
            file_path,
            file_type
        )
        
        # Return job data
        return job_data
    
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/api/jobs/{job_id}", tags=["Jobs"])
async def get_job_status(job_id: str):
    """Get the status of a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return jobs[job_id]

@app.get("/api/jobs/{job_id}/result", tags=["Jobs"])
async def get_job_result(job_id: str):
    """Get the result of a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = jobs[job_id]
    if job["status"] != "completed":
        if job["status"] == "failed":
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} failed: {job.get('message', 'Unknown error')}"
            )
        raise HTTPException(
            status_code=102,
            detail=f"Job {job_id} is still {job['status']}. Current progress: {job.get('progress', 0)}%"
        )
    
    if job_id not in job_results:
        raise HTTPException(status_code=404, detail=f"Result for job {job_id} not found")
    
    return job_results[job_id]

if __name__ == "__main__":
    # For local development
    port = int(os.getenv("PORT", "8000"))
    host = "0.0.0.0"
    print(f"Starting functional API server at http://{host}:{port}")
    print(f"API documentation available at http://{host}:{port}/docs")
    uvicorn.run("functional_api:app", host=host, port=port, reload=True)