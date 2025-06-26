"""
Router for file processing endpoints.
"""

import asyncio
import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from api.models.requests import OutputFormat, ProcessingOptions
from api.models.responses import JobResponse
from src.jobs.queue import create_job
from src.jobs.worker import process_file, get_file_type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Directory for uploaded files
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.getcwd(), "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_upload_file(upload_file: UploadFile) -> str:
    """
    Save an uploaded file to disk.
    
    Args:
        upload_file: File uploaded by the user
        
    Returns:
        Path to the saved file
    """
    # Create unique filename to avoid collisions
    file_id = uuid.uuid4().hex
    filename = f"{file_id}_{upload_file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save file to disk
    try:
        # Create upload directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write file
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
    file_type: str,
    output_format: str,
    output_dir: Optional[str] = None,
) -> None:
    """
    Process a file in the background.
    
    Args:
        job_id: Unique job identifier
        file_path: Path to the file to process
        file_type: Type of file (pdf, image, pptx, auto)
        output_format: Output format (json or files)
        output_dir: Directory to store output files
    """
    try:
        # Run the processing in a separate thread/process to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,  # Default executor
            process_file,
            job_id,
            file_path,
            file_type,
            output_format,
            output_dir
        )
    except Exception as e:
        logger.error(f"Error in background processing for job {job_id}: {str(e)}")
        # Job status is already updated by process_file


@router.post(
    "/process",
    response_model=JobResponse,
    summary="Process a file with automatic format detection",
    description="Upload a file for OCR processing with automatic format detection based on file extension",
)
async def process_file_auto(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: Optional[str] = Form(None),
) -> JobResponse:
    """
    Process a file with automatic format detection.
    """
    # Parse options or use defaults
    if options:
        import json
        try:
            options_dict = json.loads(options)
            processing_options = ProcessingOptions(**options_dict)
        except Exception as e:
            logger.error(f"Error parsing options: {str(e)}")
            processing_options = ProcessingOptions()
    else:
        processing_options = ProcessingOptions()
    
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
        job_data = create_job(file.filename, file_type)
        job_id = job_data["job_id"]
        
        # Determine output directory if needed
        output_dir = None
        if processing_options.output_format == OutputFormat.FILES:
            output_dir = os.path.join("parsed_docs", job_id)
        
        # Start background processing
        background_tasks.add_task(
            process_file_background,
            job_id,
            file_path,
            file_type,
            processing_options.output_format,
            output_dir
        )
        
        # Return job data
        return JobResponse(**job_data)
    
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.post(
    "/process/image",
    response_model=JobResponse,
    summary="Process an image file",
    description="Upload an image file for OCR text extraction",
)
async def process_image_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: Optional[str] = Form(None),
) -> JobResponse:
    """
    Process an image file for OCR.
    """
    # Check file type
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PNG and JPEG images are supported."
        )
    
    # Parse options or use defaults
    if options:
        import json
        try:
            options_dict = json.loads(options)
            processing_options = ProcessingOptions(**options_dict)
        except Exception as e:
            logger.error(f"Error parsing options: {str(e)}")
            processing_options = ProcessingOptions()
    else:
        processing_options = ProcessingOptions()
    
    try:
        # Save uploaded file
        file_path = await save_upload_file(file)
        
        # Create job
        job_data = create_job(file.filename, "image")
        job_id = job_data["job_id"]
        
        # Determine output directory if needed
        output_dir = None
        if processing_options.output_format == OutputFormat.FILES:
            output_dir = os.path.join("parsed_docs", job_id)
        
        # Start background processing
        background_tasks.add_task(
            process_file_background,
            job_id,
            file_path,
            "image",
            processing_options.output_format,
            output_dir
        )
        
        # Return job data
        return JobResponse(**job_data)
    
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@router.post(
    "/process/pdf",
    response_model=JobResponse,
    summary="Process a PDF file",
    description="Upload a PDF file for text extraction, table extraction, and OCR",
)
async def process_pdf_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: Optional[str] = Form(None),
) -> JobResponse:
    """
    Process a PDF file.
    """
    # Check file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF files are supported."
        )
    
    # Parse options or use defaults
    if options:
        import json
        try:
            options_dict = json.loads(options)
            processing_options = ProcessingOptions(**options_dict)
        except Exception as e:
            logger.error(f"Error parsing options: {str(e)}")
            processing_options = ProcessingOptions()
    else:
        processing_options = ProcessingOptions()
    
    try:
        # Save uploaded file
        file_path = await save_upload_file(file)
        
        # Create job
        job_data = create_job(file.filename, "pdf")
        job_id = job_data["job_id"]
        
        # Determine output directory if needed
        output_dir = None
        if processing_options.output_format == OutputFormat.FILES:
            output_dir = os.path.join("parsed_docs", job_id)
        
        # Start background processing
        background_tasks.add_task(
            process_file_background,
            job_id,
            file_path,
            "pdf",
            processing_options.output_format,
            output_dir
        )
        
        # Return job data
        return JobResponse(**job_data)
    
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.post(
    "/process/pptx",
    response_model=JobResponse,
    summary="Process a PowerPoint file",
    description="Upload a PPTX file for text extraction, table extraction, and OCR",
)
async def process_pptx_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: Optional[str] = Form(None),
) -> JobResponse:
    """
    Process a PowerPoint file.
    """
    # Check file type
    if not file.filename.lower().endswith((".pptx", ".ppt")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PPTX and PPT files are supported."
        )
    
    # Parse options or use defaults
    if options:
        import json
        try:
            options_dict = json.loads(options)
            processing_options = ProcessingOptions(**options_dict)
        except Exception as e:
            logger.error(f"Error parsing options: {str(e)}")
            processing_options = ProcessingOptions()
    else:
        processing_options = ProcessingOptions()
    
    try:
        # Save uploaded file
        file_path = await save_upload_file(file)
        
        # Create job
        job_data = create_job(file.filename, "pptx")
        job_id = job_data["job_id"]
        
        # Determine output directory if needed
        output_dir = None
        if processing_options.output_format == OutputFormat.FILES:
            output_dir = os.path.join("parsed_docs", job_id)
        
        # Start background processing
        background_tasks.add_task(
            process_file_background,
            job_id,
            file_path,
            "pptx",
            processing_options.output_format,
            output_dir
        )
        
        # Return job data
        return JobResponse(**job_data)
    
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing PowerPoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PowerPoint: {str(e)}")