#!/usr/bin/env python3
"""
parse_image.py

Extracts text from image files using OCR.
Supports PNG, JPEG, JPG formats.

Requirements:
    pip install pytesseract Pillow
    sudo apt install tesseract-ocr
"""

import argparse
import os
from pathlib import Path
from PIL import Image
import pytesseract


def extract_image_text(image_path):
    """
    Extract text from an image using OCR.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        str: Extracted text from the image
    """
    try:
        # Open the image
        image = Image.open(image_path)
        
        # Perform OCR on the image
        text = pytesseract.image_to_string(image)
        
        return text.strip()
        
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return f"Error processing image: {e}"


def main(args=None):
    if args is None:
        # Called directly, parse command line arguments
        parser = argparse.ArgumentParser(
            description="Extract text from image files using OCR"
        )
        parser.add_argument(
            "-i", "--input", dest="image_file", required=True,
            help="Path to input image file"
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

    # Process the image file
    source_path = Path(args.image_file)
    base_name = source_path.stem  # filename without extension
    
    if not stdout_mode:
        # Ensure output directory exists when not in stdout mode
        out_dir = Path(args.out_dir)
        out_dir.mkdir(exist_ok=True)
        out_text = out_dir / f"{base_name}.txt"

        if verbose:
            print(f"Processing image file: {args.image_file}")
            print(f"Output directory: {out_dir}")
    else:
        if verbose:
            print(f"Processing image file: {args.image_file}")
            print(f"Output mode: stdout")
            
    # Extract text from image
    extracted_text = extract_image_text(args.image_file)

    if stdout_mode:
        # Output text content to stdout
        print(extracted_text)
    else:
        # Write out extracted text to file
        with open(out_text, "w", encoding="utf-8") as f:
            f.write(extracted_text)
        print(f"Done. Text → {out_text}")


if __name__ == "__main__":
    main() 