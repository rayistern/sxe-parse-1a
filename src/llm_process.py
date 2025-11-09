"""
LLM-based document processing.
Enhances markdown conversion and removes PII using OpenAI API.
"""

import os
import logging
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

from openai import OpenAI
from openai import OpenAIError

from utils import Config, InventoryManager, chunk_text

logger = logging.getLogger('gdrive_processor.llm_process')


class LLMProcessor:
    """Handles LLM-based document processing and PII removal."""

    def __init__(self, config: Config, inventory: InventoryManager):
        self.config = config
        self.inventory = inventory

        # Get LLM configuration
        self.model = config.get('llm.model', 'gpt-4o-mini')
        self.temperature = config.get('llm.temperature', 0.1)
        self.max_chunk_size = config.get('llm.max_chunk_size', 100000)
        self.chunk_overlap = config.get('llm.chunk_overlap', 1000)
        self.max_retries = config.get('llm.max_retries', 3)
        self.timeout = config.get('llm.timeout', 120)
        self.enable_pii_removal = config.get('llm.enable_pii_removal', True)

        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=api_key)

        # Build system prompt with caching
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt for LLM processing."""
        prompt_parts = [
            "You are a document processing assistant. Your task is to convert documents to well-structured markdown.",
            "",
            "Guidelines:",
            "- Preserve all meaningful content and structure",
            "- Use proper markdown formatting (headers, lists, tables, bold, italic, code blocks)",
            "- Use ATX-style headers (# ## ###)",
            "- Maintain document hierarchy and organization",
            "- For tables, use proper markdown table syntax",
            "- For code snippets, use fenced code blocks with language identifiers",
            "- Remove any OCR artifacts or formatting errors",
            "- Improve readability while preserving original meaning",
        ]

        if self.enable_pii_removal:
            prompt_parts.extend([
                "",
                "PII Removal:",
                "- Identify and REDACT all personally identifiable information (PII)",
                "- Replace PII with [REDACTED-TYPE] placeholders:",
                "  - Names: [REDACTED-NAME]",
                "  - Email addresses: [REDACTED-EMAIL]",
                "  - Phone numbers: [REDACTED-PHONE]",
                "  - Street addresses: [REDACTED-ADDRESS]",
                "  - Social Security Numbers: [REDACTED-SSN]",
                "  - Credit card numbers: [REDACTED-CCN]",
                "  - Dates of birth: [REDACTED-DOB]",
                "  - Other sensitive data: [REDACTED-PII]",
                "- Preserve generic company names, organizations, and public entities",
                "- Keep job titles, departments, and roles if not tied to specific individuals",
            ])

        return '\n'.join(prompt_parts)

    def process_document(
        self,
        content: str,
        filename: str,
        file_id: str
    ) -> Optional[str]:
        """
        Process a document with LLM.

        Args:
            content: Document content (raw or markdown)
            filename: Original filename for context
            file_id: File ID for logging

        Returns:
            Processed markdown content, or None if failed
        """
        try:
            # Check if content needs chunking
            if len(content) > self.max_chunk_size:
                logger.info(f"Chunking large document {file_id} ({len(content)} chars)")
                return self._process_chunked_document(content, filename, file_id)
            else:
                return self._process_single_chunk(content, filename, file_id)

        except Exception as e:
            logger.error(f"Error processing document {file_id}: {e}")
            return None

    def _process_single_chunk(
        self,
        content: str,
        filename: str,
        file_id: str,
        retry_count: int = 0
    ) -> Optional[str]:
        """Process a single chunk with LLM."""
        try:
            user_prompt = f"Process the following document and convert it to clean, well-structured markdown.\n\nFilename: {filename}\n\nContent:\n{content}"

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                timeout=self.timeout
            )

            # Extract response
            processed_content = response.choices[0].message.content

            logger.debug(f"Successfully processed {file_id} with LLM")
            return processed_content

        except OpenAIError as e:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                logger.warning(
                    f"API error for {file_id}, retrying in {wait_time}s "
                    f"(attempt {retry_count + 1}/{self.max_retries}): {e}"
                )
                time.sleep(wait_time)
                return self._process_single_chunk(content, filename, file_id, retry_count + 1)
            else:
                logger.error(f"Max retries reached for {file_id}: {e}")
                return None

        except Exception as e:
            logger.error(f"Unexpected error processing {file_id}: {e}")
            return None

    def _process_chunked_document(
        self,
        content: str,
        filename: str,
        file_id: str
    ) -> Optional[str]:
        """Process a large document in chunks."""
        try:
            # Split into chunks
            chunks = chunk_text(content, self.max_chunk_size, self.chunk_overlap)

            logger.info(f"Processing {len(chunks)} chunks for {file_id}")

            processed_chunks = []

            for i, chunk in enumerate(chunks, 1):
                logger.debug(f"Processing chunk {i}/{len(chunks)} for {file_id}")

                # Add context about chunk position
                chunk_prompt = f"This is part {i} of {len(chunks)} of the document.\n\n{chunk}"

                processed_chunk = self._process_single_chunk(chunk_prompt, filename, f"{file_id}_chunk{i}")

                if processed_chunk:
                    processed_chunks.append(processed_chunk)
                else:
                    logger.warning(f"Failed to process chunk {i} of {file_id}")
                    # Continue with other chunks

            if not processed_chunks:
                logger.error(f"No chunks successfully processed for {file_id}")
                return None

            # Combine chunks
            combined_content = "\n\n".join(processed_chunks)

            return combined_content

        except Exception as e:
            logger.error(f"Error in chunked processing for {file_id}: {e}")
            return None

    def process_converted_files(self, max_files: Optional[int] = None) -> Dict[str, Any]:
        """
        Process all converted files with LLM.

        Args:
            max_files: Optional limit on number of files to process

        Returns:
            Dictionary with processing statistics
        """
        # Get files with status 'converted'
        converted_files = self.inventory.get_files_by_status('converted')

        if max_files:
            converted_files = converted_files[:max_files]

        stats = {
            'total': len(converted_files),
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        logger.info(f"Starting LLM processing of {len(converted_files)} files...")

        for file_data in converted_files:
            file_id = file_data['file_id']
            filename = file_data['filename']

            # Read converted markdown
            input_path = f"data/converted/{file_id}.md"

            if not os.path.exists(input_path):
                logger.warning(f"Converted file not found: {input_path}")
                stats['skipped'] += 1
                continue

            logger.info(f"Processing {file_id}: {filename}")

            try:
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Process with LLM
                processed_content = self.process_document(content, filename, file_id)

                if processed_content:
                    # Save processed markdown
                    output_dir = "data/processed"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = f"{output_dir}/{file_id}.md"

                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(processed_content)

                    # Update inventory
                    file_data['status'] = 'processed'
                    file_data['error_message'] = ''
                    self.inventory.add_or_update_file(file_data)
                    stats['success'] += 1
                else:
                    # Mark as failed
                    file_data['status'] = 'processing_failed'
                    file_data['error_message'] = 'LLM processing failed'
                    self.inventory.add_or_update_file(file_data)
                    stats['failed'] += 1

            except Exception as e:
                logger.error(f"Error processing {file_id}: {e}")
                file_data['status'] = 'processing_failed'
                file_data['error_message'] = str(e)
                self.inventory.add_or_update_file(file_data)
                stats['failed'] += 1

        logger.info(
            f"LLM processing complete. Success: {stats['success']}, "
            f"Failed: {stats['failed']}, Skipped: {stats['skipped']}"
        )

        return stats


def process_files_with_llm(
    config: Config,
    inventory: InventoryManager,
    max_files: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function to process files with LLM.

    Args:
        config: Configuration object
        inventory: Inventory manager
        max_files: Optional limit on number of files

    Returns:
        Processing statistics
    """
    processor = LLMProcessor(config, inventory)
    return processor.process_converted_files(max_files=max_files)
