"""
Programmatic file conversion to Markdown.
Converts documents to markdown without using LLM.
"""

import os
import logging
import subprocess
from typing import Dict, Optional, Any
from pathlib import Path
import csv
import io

import pypandoc
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from docx import Document
from openpyxl import load_workbook
import pandas as pd
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from utils import Config, InventoryManager, get_file_extension, format_folder_path

logger = logging.getLogger('gdrive_processor.convert')


class DocumentConverter:
    """Handles programmatic conversion of documents to Markdown."""

    def __init__(self, config: Config, inventory: InventoryManager):
        self.config = config
        self.inventory = inventory
        self.ocr_enabled = config.get('ocr.enabled', True)
        self.ocr_language = config.get('ocr.language', 'eng')
        self.ocr_dpi = config.get('ocr.dpi', 300)

    def convert_file(
        self,
        file_id: str,
        input_path: str,
        output_dir: str = "data/converted"
    ) -> Optional[str]:
        """
        Convert a file to Markdown.

        Args:
            file_id: Internal file ID
            input_path: Path to input file
            output_dir: Directory for output files

        Returns:
            Path to converted markdown file, or None if failed
        """
        try:
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)

            # Get file extension
            extension = get_file_extension(input_path)

            # Route to appropriate converter
            if extension in ['docx', 'doc', 'odt']:
                return self._convert_word_document(file_id, input_path, output_dir)
            elif extension == 'pdf':
                return self._convert_pdf(file_id, input_path, output_dir)
            elif extension in ['xlsx', 'xls', 'csv']:
                return self._convert_spreadsheet(file_id, input_path, output_dir)
            elif extension in ['html', 'htm']:
                return self._convert_html(file_id, input_path, output_dir)
            elif extension in ['txt', 'md']:
                return self._convert_text(file_id, input_path, output_dir)
            else:
                logger.warning(f"No converter for extension: {extension}")
                return None

        except Exception as e:
            logger.error(f"Error converting file {file_id}: {e}")
            return None

    def _convert_word_document(
        self,
        file_id: str,
        input_path: str,
        output_dir: str
    ) -> Optional[str]:
        """Convert Word document to Markdown using pandoc."""
        try:
            output_path = os.path.join(output_dir, f"{file_id}.md")

            # Use pandoc for conversion
            pypandoc.convert_file(
                input_path,
                'md',
                outputfile=output_path,
                extra_args=['--wrap=none', '--markdown-headings=atx']
            )

            logger.info(f"Converted Word document: {file_id}")
            return output_path

        except Exception as e:
            logger.error(f"Error converting Word document {file_id}: {e}")
            return None

    def _convert_pdf(
        self,
        file_id: str,
        input_path: str,
        output_dir: str
    ) -> Optional[str]:
        """Convert PDF to Markdown (with OCR if enabled)."""
        try:
            output_path = os.path.join(output_dir, f"{file_id}.md")
            text_content = []

            # Try text extraction first
            with pdfplumber.open(input_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()

                    if text and text.strip():
                        text_content.append(f"## Page {page_num}\n\n{text}\n")
                    elif self.ocr_enabled:
                        # Fall back to OCR for pages without text
                        logger.debug(f"Running OCR on page {page_num} of {file_id}")
                        ocr_text = self._ocr_pdf_page(input_path, page_num)
                        if ocr_text:
                            text_content.append(f"## Page {page_num}\n\n{ocr_text}\n")

            # Save markdown
            if text_content:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(text_content))

                logger.info(f"Converted PDF: {file_id}")
                return output_path
            else:
                logger.warning(f"No text extracted from PDF: {file_id}")
                return None

        except Exception as e:
            logger.error(f"Error converting PDF {file_id}: {e}")
            return None

    def _ocr_pdf_page(self, pdf_path: str, page_num: int) -> Optional[str]:
        """Run OCR on a specific PDF page."""
        try:
            # Convert PDF page to image
            images = convert_from_path(
                pdf_path,
                dpi=self.ocr_dpi,
                first_page=page_num,
                last_page=page_num
            )

            if not images:
                return None

            # Run OCR
            text = pytesseract.image_to_string(
                images[0],
                lang=self.ocr_language
            )

            return text.strip()

        except Exception as e:
            logger.error(f"OCR error on page {page_num}: {e}")
            return None

    def _convert_spreadsheet(
        self,
        file_id: str,
        input_path: str,
        output_dir: str
    ) -> Optional[str]:
        """Convert spreadsheet to Markdown tables."""
        try:
            output_path = os.path.join(output_dir, f"{file_id}.md")
            extension = get_file_extension(input_path)
            markdown_content = []

            if extension == 'csv':
                # Read CSV
                df = pd.read_csv(input_path)
                markdown_content.append(df.to_markdown(index=False))

            else:
                # Read Excel file (potentially multiple sheets)
                excel_file = pd.ExcelFile(input_path)

                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)

                    # Add sheet header
                    if len(excel_file.sheet_names) > 1:
                        markdown_content.append(f"## Sheet: {sheet_name}\n")

                    # Convert to markdown table
                    markdown_content.append(df.to_markdown(index=False))
                    markdown_content.append("\n")

            # Save markdown
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(markdown_content))

            logger.info(f"Converted spreadsheet: {file_id}")
            return output_path

        except Exception as e:
            logger.error(f"Error converting spreadsheet {file_id}: {e}")
            return None

    def _convert_html(
        self,
        file_id: str,
        input_path: str,
        output_dir: str
    ) -> Optional[str]:
        """Convert HTML to Markdown."""
        try:
            output_path = os.path.join(output_dir, f"{file_id}.md")

            # Read HTML
            with open(input_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Convert to markdown
            markdown_content = md(html_content, heading_style="ATX")

            # Save markdown
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            logger.info(f"Converted HTML: {file_id}")
            return output_path

        except Exception as e:
            logger.error(f"Error converting HTML {file_id}: {e}")
            return None

    def _convert_text(
        self,
        file_id: str,
        input_path: str,
        output_dir: str
    ) -> Optional[str]:
        """Convert plain text or markdown (copy with minimal processing)."""
        try:
            output_path = os.path.join(output_dir, f"{file_id}.md")

            # Read and copy content
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Save as markdown
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Converted text file: {file_id}")
            return output_path

        except Exception as e:
            logger.error(f"Error converting text file {file_id}: {e}")
            return None

    def convert_downloaded_files(self) -> Dict[str, Any]:
        """
        Convert all downloaded files to Markdown.

        Returns:
            Dictionary with conversion statistics
        """
        # Get files with status 'downloaded'
        downloaded_files = self.inventory.get_files_by_status('downloaded')

        stats = {
            'total': len(downloaded_files),
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        logger.info(f"Starting conversion of {len(downloaded_files)} files...")

        for file_data in downloaded_files:
            file_id = file_data['file_id']
            filename = file_data['filename']

            # Determine input path
            extension = get_file_extension(filename)
            input_path = f"data/raw/{file_id}.{extension}"

            # Handle exported Google formats
            if not os.path.exists(input_path):
                # Try common export extensions
                for ext in ['.docx', '.xlsx', '.pptx', '.pdf']:
                    test_path = f"data/raw/{file_id}{ext}"
                    if os.path.exists(test_path):
                        input_path = test_path
                        break

            if not os.path.exists(input_path):
                logger.warning(f"Input file not found: {input_path}")
                stats['skipped'] += 1
                continue

            logger.info(f"Converting {file_id}: {filename}")

            # Convert file
            output_path = self.convert_file(file_id, input_path)

            if output_path:
                # Update inventory
                file_data['status'] = 'converted'
                file_data['error_message'] = ''
                self.inventory.add_or_update_file(file_data)
                stats['success'] += 1
            else:
                # Mark as failed
                file_data['status'] = 'conversion_failed'
                file_data['error_message'] = 'Conversion failed'
                self.inventory.add_or_update_file(file_data)
                stats['failed'] += 1

        logger.info(
            f"Conversion complete. Success: {stats['success']}, "
            f"Failed: {stats['failed']}, Skipped: {stats['skipped']}"
        )

        return stats


def convert_files(config: Config, inventory: InventoryManager) -> Dict[str, Any]:
    """
    Convenience function to convert files.

    Args:
        config: Configuration object
        inventory: Inventory manager

    Returns:
        Conversion statistics
    """
    converter = DocumentConverter(config, inventory)
    return converter.convert_downloaded_files()
