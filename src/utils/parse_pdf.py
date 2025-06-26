#!/usr/bin/env python3
"""
parse_pdf.py

Extracts text, tables, and OCR from PDF files.
Supports text extraction and image OCR within PDFs.

Requirements:
    pip install unstructured[all-docs] pdf2image pytesseract
    sudo apt install poppler-utils tesseract-ocr
"""

import argparse
import os
from pathlib import Path
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Table
from pdf2image import convert_from_path
from PIL import Image
import pytesseract


def extract_pdf_text_tables_images(pdf_path, images_dir=None):
    """
    Extract text, tables, and OCR from PDF.
    
    Args:
        pdf_path: Path to the PDF file
        images_dir: Directory to save extracted images (optional)
        
    Returns:
        tuple: (text_runs, tables_html)
    """
    # 1) Partition PDF into text + tables
    elements = partition_pdf(filename=pdf_path)
    text_runs = []
    tables_html = []

    for el in elements:
        if isinstance(el, Table):
            # Render table as HTML
            try:
                # Try to get HTML from metadata first
                html = getattr(el.metadata, 'text_as_html', None)
                if not html:
                    # Fallback to converting table data to HTML
                    html = "<table>"
                    if hasattr(el, 'metadata') and hasattr(el.metadata, 'text_as_html'):
                        html = el.metadata.text_as_html
                    else:
                        # Create basic HTML table from table data
                        html = "<table><tr><td>Table content</td></tr></table>"
            except Exception as e:
                print(f"Warning: failed to render table as HTML: {e}")
                html = "<table><tr><td>Table content (rendering failed)</td></tr></table>"
            tables_html.append(html)
        else:
            text_runs.append(el.text)

    # 2) Extract and OCR images from PDF pages
    try:
        # Convert PDF pages to images
        images = convert_from_path(pdf_path)
        
        for page_idx, image in enumerate(images, start=1):
            if images_dir is not None:
                os.makedirs(images_dir, exist_ok=True)
                img_filename = os.path.join(images_dir, f"page_{page_idx}.png")
                image.save(img_filename, "PNG")
                
                # Perform OCR on the page image
                try:
                    text_from_image = pytesseract.image_to_string(image)
                    if text_from_image.strip():
                        text_runs.append(f"Page {page_idx} (OCR): {text_from_image.strip()}")
                except Exception as e:
                    print(f"Warning: OCR failed for page {page_idx}: {e}")
                    
    except Exception as e:
        print(f"Warning: Failed to extract images from PDF: {e}")

    return text_runs, tables_html


def main(args=None):
    if args is None:
        # Called directly, parse command line arguments
        parser = argparse.ArgumentParser(
            description="Extract text, tables, and OCR from PDF files"
        )
        parser.add_argument(
            "-i", "--input", dest="pdf_file", required=True,
            help="Path to input .pdf file"
        )
        parser.add_argument(
            "-o", "--out_dir", default="parsed_docs",
            help="Directory to write output files (default: parsed_docs)"
        )
        parser.add_argument(
            "-v", "--verbose", action="store_true",
            help="Enable verbose output"
        )
        parser.add_argument(
            "--stdout", action="store_true",
            help="Output text content to stdout instead of writing to files"
        )
        args = parser.parse_args()

    # Set verbosity and stdout mode based on args
    verbose = getattr(args, 'verbose', False)
    stdout_mode = getattr(args, 'stdout', False)

    # Process the PDF file
    source_path = Path(args.pdf_file)
    base_name = source_path.stem  # filename without extension
    
    # In stdout mode, we still need a temp dir for images during processing
    # but we won't write the text files to disk
    if not stdout_mode:
        # Ensure output directory exists when not in stdout mode
        out_dir = Path(args.out_dir)
        out_dir.mkdir(exist_ok=True)
        
        out_text = out_dir / f"{base_name}.txt"
        out_tables = out_dir / f"{base_name}_tables.html"
        images_dir = out_dir / base_name

        if verbose:
            print(f"Processing PDF file: {args.pdf_file}")
            print(f"Output directory: {out_dir}")
    else:
        # For stdout mode, we still need a temp dir for images
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix="ocr_convert_")
        images_dir = Path(temp_dir) / base_name
        
        if verbose:
            print(f"Processing PDF file: {args.pdf_file}")
            print(f"Temp directory for images: {images_dir}")
        
    texts, tables = extract_pdf_text_tables_images(args.pdf_file, images_dir=str(images_dir))

    if stdout_mode:
        # Output text content to stdout
        for t in texts:
            print(t.strip())
            print()
            
        if tables and verbose:
            print("\n=== Tables (HTML format) ===")
            for html in tables:
                print(html)
                print()
    else:
        # Write out all text runs to file
        with open(out_text, "w", encoding="utf-8") as f:
            for t in texts:
                f.write(t.strip() + "\n\n")

        # Write out tables as HTML
        with open(out_tables, "w", encoding="utf-8") as f:
            for html in tables:
                f.write(html + "\n\n")

        print(f"Done. Text → {out_text}; Tables → {out_tables}; Images → {images_dir}")


if __name__ == "__main__":
    main() 