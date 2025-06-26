"""
Background worker for OCR processing tasks.

This module provides the worker implementation for processing OCR jobs asynchronously.
It handles long-running OCR processes and updates job status in the queue.
"""

import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Import job queue management
from src.jobs.queue import update_job_status, store_job_result

# Import file processors
from src.utils.parse_image import extract_image_text
from src.utils.parse_pdf import extract_pdf_text_tables_images
from src.utils.parse_pptx import extract_pptx_text_tables_images

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ProcessorResult:
    """Container for processing results."""
    
    def __init__(
        self,
        texts: List[Dict[str, Any]] = None,
        tables: List[Dict[str, Any]] = None,
        images: List[Dict[str, str]] = None,
        output_files: Dict[str, str] = None
    ):
        self.texts = texts or []
        self.tables = tables or []
        self.images = images or []
        self.output_files = output_files or {}


def process_file(
    job_id: str,
    file_path: str,
    file_type: str,
    output_format: str = "json",
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process a file asynchronously.
    
    Args:
        job_id: Unique job identifier
        file_path: Path to the uploaded file
        file_type: Type of file (pdf, image, pptx, auto)
        output_format: Output format (json or files)
        output_dir: Directory to store output files (if output_format is 'files')
        
    Returns:
        Dictionary with processing results
    """
    try:
        # Update job status to processing
        update_job_status(job_id, "processing", progress=10, 
                          message=f"Starting {file_type} processing")
        
        # Create temp dir for processing if needed
        if output_format == "files":
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            else:
                output_dir = os.path.join("parsed_docs", job_id)
                os.makedirs(output_dir, exist_ok=True)
        else:
            # For JSON output, still need temp dir for some file types
            temp_dir = tempfile.mkdtemp(prefix=f"ocr_{job_id}_")
            output_dir = temp_dir
        
        # Process based on file type
        file_name = os.path.basename(file_path)
        result = ProcessorResult()
        
        if file_type == "auto":
            # Determine file type from extension
            file_type = get_file_type(file_path)
            if not file_type:
                raise ValueError(f"Unsupported file type for {file_path}")
        
        update_job_status(job_id, "processing", progress=20, 
                          message=f"Detected file type: {file_type}")
        
        # Process file based on type
        if file_type == "image":
            result = process_image(job_id, file_path, output_dir)
        elif file_type == "pdf":
            result = process_pdf(job_id, file_path, output_dir)
        elif file_type == "pptx":
            result = process_pptx(job_id, file_path, output_dir)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Create result object
        processing_result = {
            "job_id": job_id,
            "file_name": file_name,
            "file_type": file_type,
            "texts": result.texts,
            "tables": result.tables,
            "images": result.images,
            "output_files": result.output_files,
            "metadata": {
                "output_format": output_format,
                "output_directory": output_dir if output_format == "files" else None,
            }
        }
        
        # If output format is JSON and we created a temp dir, clean it up
        if output_format == "json" and "temp_dir" in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Update job status to completed
        update_job_status(job_id, "completed", progress=100, 
                          message="Processing completed successfully")
        
        # Store result
        store_job_result(job_id, processing_result)
        
        return processing_result
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
        # Update job status to failed
        update_job_status(job_id, "failed", message=f"Processing failed: {str(e)}")
        
        # If we created a temp dir, clean it up
        if "temp_dir" in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Re-raise exception for caller
        raise


def get_file_type(file_path: str) -> Optional[str]:
    """
    Determine file type based on file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File type (image, pdf, pptx) or None if unsupported
    """
    ext = Path(file_path).suffix.lower()
    
    file_type_map = {
        '.pptx': 'pptx',
        '.ppt': 'pptx',
        '.png': 'image',
        '.jpeg': 'image',
        '.jpg': 'image',
        '.pdf': 'pdf',
    }
    
    return file_type_map.get(ext)


def process_image(job_id: str, file_path: str, output_dir: str) -> ProcessorResult:
    """
    Process an image file.
    
    Args:
        job_id: Unique job identifier
        file_path: Path to the image file
        output_dir: Directory to store output files
        
    Returns:
        ProcessorResult object with extracted text
    """
    update_job_status(job_id, "processing", progress=30, 
                      message="Applying OCR to image")
    
    # Extract text using OCR
    extracted_text = extract_image_text(file_path)
    
    # Create output file path
    base_name = Path(file_path).stem
    out_text = os.path.join(output_dir, f"{base_name}.txt")
    
    # Write text to file
    with open(out_text, "w", encoding="utf-8") as f:
        f.write(extracted_text)
    
    update_job_status(job_id, "processing", progress=90, 
                      message="OCR completed, preparing results")
    
    # Create result object
    result = ProcessorResult()
    result.texts = [{
        "text": extracted_text,
        "source": "image",
        "page_number": None
    }]
    result.output_files = {"text": out_text}
    
    return result


def process_pdf(job_id: str, file_path: str, output_dir: str) -> ProcessorResult:
    """
    Process a PDF file.
    
    Args:
        job_id: Unique job identifier
        file_path: Path to the PDF file
        output_dir: Directory to store output files
        
    Returns:
        ProcessorResult object with extracted text, tables, and images
    """
    update_job_status(job_id, "processing", progress=30, 
                      message="Extracting text and tables from PDF")
    
    # Create images directory
    base_name = Path(file_path).stem
    images_dir = os.path.join(output_dir, base_name)
    os.makedirs(images_dir, exist_ok=True)
    
    # Extract text, tables, and images
    texts, tables_html = extract_pdf_text_tables_images(file_path, images_dir=images_dir)
    
    # Create output file paths
    out_text = os.path.join(output_dir, f"{base_name}.txt")
    out_tables = os.path.join(output_dir, f"{base_name}_tables.html")
    
    update_job_status(job_id, "processing", progress=70, 
                      message="Processing PDF pages")
    
    # Write text to file
    with open(out_text, "w", encoding="utf-8") as f:
        for t in texts:
            f.write(t.strip() + "\n\n")
    
    # Write tables to file
    with open(out_tables, "w", encoding="utf-8") as f:
        for html in tables_html:
            f.write(html + "\n\n")
    
    update_job_status(job_id, "processing", progress=90, 
                      message="PDF processing completed, preparing results")
    
    # Get image files
    image_files = []
    if os.path.exists(images_dir):
        for img_file in os.listdir(images_dir):
            if img_file.startswith("page_") and img_file.endswith(".png"):
                try:
                    page_num = int(img_file.replace("page_", "").replace(".png", ""))
                    image_files.append({
                        "path": os.path.join(images_dir, img_file),
                        "source": "page",
                        "page_number": page_num
                    })
                except ValueError:
                    # If page number can't be parsed, just add the image without a page number
                    image_files.append({
                        "path": os.path.join(images_dir, img_file),
                        "source": "page",
                        "page_number": None
                    })
    
    # Create result object
    result = ProcessorResult()
    
    # Add texts with page numbers if available
    text_entries = []
    for text in texts:
        # Try to extract page number if it's in OCR format "Page X (OCR): ..."
        page_num = None
        source = "text"
        
        if text.startswith("Page ") and " (OCR): " in text:
            try:
                page_part = text.split(" (OCR): ")[0]
                page_num = int(page_part.replace("Page ", ""))
                source = "ocr"
                # Remove the page prefix for cleaner output
                text = text.split(" (OCR): ", 1)[1]
            except ValueError:
                pass
        
        text_entries.append({
            "text": text,
            "source": source,
            "page_number": page_num
        })
    
    result.texts = text_entries
    
    # Add tables
    result.tables = [{"html": html, "source": "pdf", "page_number": None} for html in tables_html]
    result.images = image_files
    result.output_files = {
        "text": out_text, 
        "tables": out_tables, 
        "images_dir": images_dir
    }
    
    return result


def process_pptx(job_id: str, file_path: str, output_dir: str) -> ProcessorResult:
    """
    Process a PowerPoint file.
    
    Args:
        job_id: Unique job identifier
        file_path: Path to the PPTX file
        output_dir: Directory to store output files
        
    Returns:
        ProcessorResult object with extracted text, tables, and images
    """
    update_job_status(job_id, "processing", progress=30, 
                      message="Extracting content from PowerPoint")
    
    # Create images directory
    base_name = Path(file_path).stem
    images_dir = os.path.join(output_dir, base_name)
    os.makedirs(images_dir, exist_ok=True)
    
    # Extract text, tables, and images
    texts, tables_html = extract_pptx_text_tables_images(file_path, images_dir=images_dir)
    
    # Create output file paths
    out_text = os.path.join(output_dir, f"{base_name}.txt")
    out_tables = os.path.join(output_dir, f"{base_name}_tables.html")
    
    update_job_status(job_id, "processing", progress=70, 
                      message="Processing PowerPoint slides")
    
    # Write text to file
    with open(out_text, "w", encoding="utf-8") as f:
        for t in texts:
            f.write(t.strip() + "\n\n")
    
    # Write tables to file
    with open(out_tables, "w", encoding="utf-8") as f:
        for html in tables_html:
            f.write(html + "\n\n")
    
    update_job_status(job_id, "processing", progress=90, 
                      message="PowerPoint processing completed, preparing results")
    
    # Get image files
    image_files = []
    if os.path.exists(images_dir):
        for img_file in os.listdir(images_dir):
            if img_file.startswith("slide") and "_img" in img_file:
                try:
                    # Extract slide and image numbers from filename (e.g., slide3_img2.png)
                    slide_part = img_file.split("_")[0]
                    slide_num = int(slide_part.replace("slide", ""))
                    image_files.append({
                        "path": os.path.join(images_dir, img_file),
                        "source": "slide",
                        "page_number": slide_num
                    })
                except ValueError:
                    # If slide number can't be parsed, just add the image without a slide number
                    image_files.append({
                        "path": os.path.join(images_dir, img_file),
                        "source": "slide",
                        "page_number": None
                    })
    
    # Create result object
    result = ProcessorResult()
    result.texts = [{"text": t, "source": "slide", "page_number": None} for t in texts]
    result.tables = [{"html": html, "source": "slide", "page_number": None} for html in tables_html]
    result.images = image_files
    result.output_files = {
        "text": out_text, 
        "tables": out_tables, 
        "images_dir": images_dir
    }
    
    return result