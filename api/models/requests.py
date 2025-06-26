"""
Request models for the OCR API.
"""

from enum import Enum
from pydantic import BaseModel, Field


class OutputFormat(str, Enum):
    """Enum for output formats."""
    JSON = "json"
    FILES = "files"


class ProcessingOptions(BaseModel):
    """Common options for all processing requests."""
    output_format: OutputFormat = Field(
        default=OutputFormat.JSON,
        description="Format to return results in. JSON returns all data in the response, FILES stores files on disk and returns paths."
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose processing output."
    )