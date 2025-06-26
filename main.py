#!/usr/bin/env python3
"""
Main entry point for document parsing and OCR conversion.

Supports multiple file types and routes to appropriate parsers in src/utils/.
Currently supports:
- PPTX files (.pptx) - Extract text, tables, and OCR from PowerPoint files
- Image files (.png, .jpg, .jpeg) - Extract text using OCR
- PDF files (.pdf) - Extract text, tables, and OCR from PDF documents

Key features:
- Automatic file type detection based on extension
- Support for subcommands (pptx, image, pdf) for specific file types
- All arguments use keyword format (--option) rather than positional arguments
- Option to output text directly to stdout instead of writing files (--stdout)
- Detailed error handling and verbose mode for debugging (--verbose)

Basic usage:
  ocr_convert_docs -i document.pptx
  ocr_convert_docs pdf -i document.pdf -o output_dir
  ocr_convert_docs image -i scan.jpg --stdout

Use --help or the help command for detailed usage information.
"""

import argparse
import sys
import logging
from pathlib import Path

# File type detection
def get_file_type(file_path):
    """Determine file type based on file extension."""
    path = Path(file_path)
    ext = path.suffix.lower()
    
    file_type_map = {
        '.pptx': 'pptx',
        '.ppt': 'pptx',  # Treat .ppt as .pptx for now
        '.png': 'image',
        '.jpeg': 'image',
        '.jpg': 'image',
        '.pdf': 'pdf',
        # Future file types can be added here:
        # '.docx': 'docx',
        # '.doc': 'docx',
    }
    
    return file_type_map.get(ext)


def create_parser():
    """Create and return the argument parser."""
    # Main parser
    parser = argparse.ArgumentParser(
        description="Extract text, tables, and OCR from various document formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s -i document.pptx                         # Process PPTX file\n"
            "  %(prog)s pptx -i document.pptx                    # Process PPTX with specific format\n"
            "  %(prog)s image -i scan.jpg -o extracted_text      # Process image with custom output dir\n"
            "  %(prog)s pdf -i report.pdf --verbose              # Process PDF with verbose output\n"
            "  %(prog)s --version                               # Show version information\n"
            "  %(prog)s -i document.pptx --stdout               # Output text to stdout instead of files"
        )
    )
    
    # Add global arguments
    parser.add_argument(
        "--version", action="version", version="OCR Document Converter 1.0.0"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--stdout", action="store_true",
        help="Output text content to stdout instead of writing to files"
    )
    
    # Create subparsers for different file types
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Common parser that handles automatic file type detection
    auto_parser = subparsers.add_parser("auto", help="Automatically detect file type and process accordingly")
    auto_parser.add_argument(
        "-i", "--input", dest="input_file", required=True,
        help="Path to input document file"
    )
    auto_parser.add_argument(
        "-o", "--out_dir", default="parsed_docs",
        help="Directory to write output files (default: parsed_docs)"
    )
    auto_parser.add_argument(
        "--stdout", action="store_true",
        help="Output text content to stdout instead of writing to files"
    )
    auto_parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose output"
    )
    
    # PPTX parser
    pptx_parser = subparsers.add_parser("pptx", help="Process PowerPoint (.pptx) files")
    pptx_parser.add_argument(
        "-i", "--input", dest="pptx_file", required=True,
        help="Path to input .pptx file"
    )
    pptx_parser.add_argument(
        "-o", "--out_dir", default="parsed_docs",
        help="Directory to write output files (default: parsed_docs)"
    )
    pptx_parser.add_argument(
        "--stdout", action="store_true",
        help="Output text content to stdout instead of writing to files"
    )
    pptx_parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose output"
    )
    
    # Image parser
    image_parser = subparsers.add_parser("image", help="Process image files (.png, .jpg, .jpeg)")
    image_parser.add_argument(
        "-i", "--input", dest="image_file", required=True,
        help="Path to input image file"
    )
    image_parser.add_argument(
        "-o", "--out_dir", default="parsed_docs",
        help="Directory to write output files (default: parsed_docs)"
    )
    image_parser.add_argument(
        "--stdout", action="store_true",
        help="Output text content to stdout instead of writing to files"
    )
    image_parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose output"
    )
    
    # PDF parser
    pdf_parser = subparsers.add_parser("pdf", help="Process PDF (.pdf) files")
    pdf_parser.add_argument(
        "-i", "--input", dest="pdf_file", required=True,
        help="Path to input .pdf file"
    )
    pdf_parser.add_argument(
        "-o", "--out_dir", default="parsed_docs",
        help="Directory to write output files (default: parsed_docs)"
    )
    pdf_parser.add_argument(
        "--stdout", action="store_true",
        help="Output text content to stdout instead of writing to files"
    )
    pdf_parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose output"
    )
    
    # For backward compatibility, allow input file to be specified directly without a subcommand
    parser.add_argument(
        "-i", "--input", dest="input_file",
        help="Path to input document file"
    )
    parser.add_argument(
        "-o", "--out_dir", default="parsed_docs",
        help="Directory to write output files (default: parsed_docs)"
    )
    
    return parser


def process_pptx(args):
    """Process a PPTX file."""
    from src.utils.parse_pptx import main as pptx_main
    logging.info(f"Processing PPTX file: {args.pptx_file}")
    pptx_main(args)
    

def process_image(args):
    """Process an image file."""
    from src.utils.parse_image import main as image_main
    logging.info(f"Processing image file: {args.image_file}")
    image_main(args)
    

def process_pdf(args):
    """Process a PDF file."""
    from src.utils.parse_pdf import main as pdf_main
    logging.info(f"Processing PDF file: {args.pdf_file}")
    pdf_main(args)


def process_auto(args):
    """Process a file by automatically detecting its type."""
    # Check if input file exists
    if not args.input_file:
        logging.error("Error: No input file specified. Use -i/--input to specify a file.")
        sys.exit(1)
        
    input_path = Path(args.input_file)
    if not input_path.exists():
        logging.error(f"Error: Input file '{args.input_file}' does not exist.")
        logging.error(f"Please provide a valid file path.")
        sys.exit(1)

    # Determine file type
    file_type = get_file_type(args.input_file)
    if not file_type:
        logging.error(f"Error: Unsupported file type '{input_path.suffix}'.")
        logging.error(f"Supported file types: .pptx, .ppt, .png, .jpg, .jpeg, .pdf")
        logging.error(f"Use the appropriate subcommand for your file type: pptx, image, or pdf")
        sys.exit(1)

    # Route to appropriate parser based on file type
    try:
        if file_type == 'pptx':
            args.pptx_file = args.input_file
            process_pptx(args)
        elif file_type == 'image':
            args.image_file = args.input_file
            process_image(args)
        elif file_type == 'pdf':
            args.pdf_file = args.input_file
            process_pdf(args)
        else:
            logging.error(f"Error: Parser for file type '{file_type}' not implemented yet.")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Error processing {args.input_file}: {str(e)}")
        if args.verbose:
            # Show the full traceback in verbose mode
            import traceback
            logging.error(traceback.format_exc())
        else:
            logging.error("Run with --verbose for more detailed error information.")
        sys.exit(1)


def main():
    try:
        # Create parser and parse arguments
        parser = create_parser()
        args = parser.parse_args()
        
        # Configure logging based on verbosity level
        log_level = logging.DEBUG if args.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(levelname)s: %(message)s"
        )
        
        # If input file is provided without a subcommand, use auto mode
        if not args.command and args.input_file:
            args.command = "auto"
        # If no command and no input file, show help
        elif not args.command:
            parser.print_help()
            return
            
        # Route to appropriate command handler
        if args.command == "pptx":
            if not hasattr(args, 'pptx_file') or not args.pptx_file:
                logging.error("Error: No input file specified. Use -i/--input to specify a file.")
                return
            process_pptx(args)
        elif args.command == "image":
            if not hasattr(args, 'image_file') or not args.image_file:
                logging.error("Error: No input file specified. Use -i/--input to specify a file.")
                return
            process_image(args)
        elif args.command == "pdf":
            if not hasattr(args, 'pdf_file') or not args.pdf_file:
                logging.error("Error: No input file specified. Use -i/--input to specify a file.")
                return
            process_pdf(args)
        elif args.command == "auto":
            if not hasattr(args, 'input_file') or not args.input_file:
                logging.error("Error: No input file specified. Use -i/--input to specify a file.")
                return
            process_auto(args)
        
        # Determine which input file was used
        input_file = None
        if args.command == "auto" and hasattr(args, 'input_file'):
            input_file = args.input_file
        elif hasattr(args, f"{args.command}_file"):
            input_file = getattr(args, f"{args.command}_file")
            
        if input_file:
            logging.info(f"Processing complete for {input_file}")
        
    except KeyboardInterrupt:
        logging.error("\nProcess interrupted by user. Exiting...")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        if getattr(args, 'verbose', False):
            # Show the full traceback in verbose mode
            import traceback
            logging.error(traceback.format_exc())
        else:
            logging.error("Run with --verbose for more detailed error information.")
        sys.exit(1)


if __name__ == "__main__":
    main()
