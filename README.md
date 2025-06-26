# Owl OCR

A versatile document parsing and OCR conversion tool that extracts text, tables, and other content from various file formats.

## Installation

Owl OCR requires both Python dependencies and system packages to function properly.

### System Requirements (Ubuntu)

Install the required system packages:

```bash
sudo apt update
sudo apt install -y \
    tesseract-ocr \
    poppler-utils \
    libreoffice-writer \
    libreoffice-core
```

### Python Environment

Owl OCR uses `uv` for Python dependency management. First, install `uv`:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

Next, clone the repository and set up the Python environment:

```bash
# Clone the repository
git clone https://github.com/your-username/owl-ocr.git
cd owl-ocr

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies using uv
uv sync
```

## Overview

Owl OCR is designed to automatically detect file types and apply appropriate parsing techniques to extract text and content. The tool currently supports:

- **PowerPoint files** (.pptx, .ppt) - Extract text, tables, and perform OCR on slides
- **Images** (.png, .jpg, .jpeg) - Extract text using OCR
- **PDF documents** (.pdf) - Extract text, tables, and perform OCR on pages

## Features

- Automatic file type detection based on extension
- Support for direct subcommands (pptx, image, pdf) for specific file types
- Option to output text directly to stdout instead of writing files
- Detailed error handling and verbose mode for debugging

## Usage

### Basic Usage

```bash
# Automatically detect file type
ocr_convert_docs -i document.pptx

# Process a PDF file with explicit format
ocr_convert_docs pdf -i document.pdf -o output_dir

# Process an image and output to stdout
ocr_convert_docs image -i scan.jpg --stdout

# Show version information
ocr_convert_docs --version

# Show help
ocr_convert_docs --help
```

### Command-line Options

| Option | Description |
|--------|-------------|
| `-i, --input` | Path to input file (required) |
| `-o, --out_dir` | Directory to write output files (default: parsed_docs) |
| `--stdout` | Output text content to stdout instead of writing to files |
| `-v, --verbose` | Enable verbose output for debugging |
| `--version` | Show version information |
| `--help` | Show help message |

### File Type Subcommands

- `pptx`: Process PowerPoint files
- `image`: Process image files
- `pdf`: Process PDF files
- `auto`: Automatically detect file type (default if no subcommand is specified)

Each subcommand accepts the same parameters as the main command.

## Examples

```bash
# Process a PowerPoint presentation
ocr_convert_docs -i presentation.pptx

# Process a PDF with custom output directory
ocr_convert_docs pdf -i document.pdf -o extracted_text

# Process an image with verbose logging
ocr_convert_docs image -i scan.jpg -v

# Output directly to stdout instead of files
ocr_convert_docs -i document.pdf --stdout
```

## API Server

Owl OCR also includes a FastAPI server that exposes OCR functionality through HTTP endpoints.

### Starting the API Server

```bash
# Start the API server
python run_api.py

# Or directly with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API server will start at http://localhost:8000 and the interactive API documentation is available at http://localhost:8000/docs

### API Endpoints

#### File Processing Endpoints

- `POST /api/process` - Process a file with automatic format detection
- `POST /api/process/image` - Process image files (.png, .jpg, .jpeg)
- `POST /api/process/pdf` - Process PDF documents (.pdf)
- `POST /api/process/pptx` - Process PowerPoint files (.pptx, .ppt)

#### Job Management Endpoints

- `GET /api/jobs/{job_id}` - Get job status
- `GET /api/jobs/{job_id}/result` - Get job results
- `DELETE /api/jobs/{job_id}` - Delete a job

### Handling Long-Running Jobs

The API implements an asynchronous job system to handle long-running OCR processes:

1. When a file is uploaded, a job is created and processing begins in the background
2. The API immediately returns a job ID that can be used to check status
3. The client can poll the job status endpoint until processing is complete
4. Once completed, results can be retrieved from the result endpoint

This approach ensures that large files or complex processing tasks don't cause timeouts.

## Dependencies

### Python Packages
- pillow: Image processing library
- pytesseract: Python wrapper for Tesseract OCR engine
- unstructured[all-docs]: Document processing framework
- python-pptx: PowerPoint file processing
- pdf2image: Convert PDF to images for OCR

### System Dependencies
- tesseract-ocr: OCR engine for text extraction from images
- poppler-utils: Required for PDF processing
- libreoffice-writer and libreoffice-core: Required for processing WMF/EMF images in PowerPoint presentations