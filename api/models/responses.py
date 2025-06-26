"""
Response models for the OCR API.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Enum for job status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobResponse(BaseModel):
    """Response model for job creation and status."""
    job_id: str = Field(..., description="Unique identifier for the job")
    status: JobStatus = Field(..., description="Current status of the job")
    file_name: str = Field(..., description="Original file name that was processed")
    file_type: str = Field(..., description="Detected file type")
    created_at: str = Field(..., description="Timestamp when job was created")
    updated_at: str = Field(..., description="Timestamp when job status was last updated")
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)")
    message: Optional[str] = Field(None, description="Status or error message")


class TextExtraction(BaseModel):
    """Text extraction result model."""
    text: str = Field(..., description="Extracted text content")
    source: str = Field(..., description="Source of the text (e.g., 'page', 'slide', 'image')")
    page_number: Optional[int] = Field(None, description="Page or slide number if applicable")


class TableExtraction(BaseModel):
    """Table extraction result model."""
    html: str = Field(..., description="Table content as HTML")
    source: str = Field(..., description="Source of the table (e.g., 'page', 'slide')")
    page_number: Optional[int] = Field(None, description="Page or slide number if applicable")


class ImageFile(BaseModel):
    """Image file reference model."""
    path: str = Field(..., description="Path to the image file")
    source: str = Field(..., description="Source of the image (e.g., 'page', 'slide')")
    page_number: Optional[int] = Field(None, description="Page or slide number if applicable")


class ProcessingResult(BaseModel):
    """Complete processing result model."""
    job_id: str = Field(..., description="Unique identifier for the job")
    file_name: str = Field(..., description="Original file name that was processed")
    file_type: str = Field(..., description="Detected file type")
    texts: List[TextExtraction] = Field(default_factory=list, description="Extracted text content")
    tables: List[TableExtraction] = Field(default_factory=list, description="Extracted tables as HTML")
    images: List[ImageFile] = Field(default_factory=list, description="Paths to extracted images")
    output_files: Dict[str, str] = Field(default_factory=dict, description="Map of output file types to their paths")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the processing")