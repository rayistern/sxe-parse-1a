"""
Master markdown assembly module.
Combines all processed markdown files into a single knowledge base.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from utils import Config, InventoryManager, format_folder_path

logger = logging.getLogger('gdrive_processor.assemble')


class MarkdownAssembler:
    """Assembles individual markdown files into a master knowledge base."""

    def __init__(self, config: Config, inventory: InventoryManager):
        self.config = config
        self.inventory = inventory

        # Get configuration
        self.include_toc = config.get('output.include_toc', True)
        self.include_metadata = config.get('output.include_metadata', True)
        self.folder_separator = config.get('output.folder_separator', ' > ')
        self.section_separator = config.get('output.section_separator', '\n\n---\n\n')
        self.master_file = config.get('output.master_file', 'data/output/knowledge_base.md')
        self.save_individual = config.get('output.save_individual_files', True)

    def assemble_knowledge_base(
        self,
        use_llm_processed: bool = True,
        sort_by: str = 'path'
    ) -> Dict[str, Any]:
        """
        Assemble all processed files into master markdown.

        Args:
            use_llm_processed: If True, use LLM-processed files; otherwise use converted files
            sort_by: Sort order (path, name, date, size, type)

        Returns:
            Dictionary with assembly statistics
        """
        # Determine which files to use
        if use_llm_processed:
            status_filter = 'processed'
            source_dir = 'data/processed'
        else:
            # Use converted files (either 'converted' or 'processed' status)
            files_converted = self.inventory.get_files_by_status('converted')
            files_processed = self.inventory.get_files_by_status('processed')
            all_files = files_converted + files_processed
            source_dir = 'data/converted'  # Will check both directories

            # For this case, we'll handle file lookup differently
            return self._assemble_mixed_sources(all_files, sort_by)

        # Get files with the specified status
        files = self.inventory.get_files_by_status(status_filter)

        return self._assemble_from_files(files, source_dir, sort_by)

    def _assemble_mixed_sources(
        self,
        files: List[Dict[str, Any]],
        sort_by: str
    ) -> Dict[str, Any]:
        """Assemble from mixed sources (converted and processed)."""
        stats = {
            'total_files': len(files),
            'included': 0,
            'skipped': 0,
            'output_path': self.master_file
        }

        # Sort files
        sorted_files = self._sort_files(files, sort_by)

        # Prepare output
        master_content = []

        # Add header
        master_content.append(self._generate_header())

        # Add table of contents if enabled
        if self.include_toc:
            master_content.append(self._generate_toc(sorted_files))

        # Process each file
        for file_data in sorted_files:
            file_id = file_data['file_id']

            # Try processed first, then converted
            content = None
            for source_dir in ['data/processed', 'data/converted']:
                file_path = f"{source_dir}/{file_id}.md"
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        break
                    except Exception as e:
                        logger.error(f"Error reading {file_path}: {e}")
                        continue

            if not content:
                logger.warning(f"No markdown file found for {file_id}")
                stats['skipped'] += 1
                continue

            # Build document section
            section = self._build_document_section(file_data, content)
            master_content.append(section)
            stats['included'] += 1

        # Combine all content
        final_content = '\n'.join(master_content)

        # Save master file
        os.makedirs(os.path.dirname(self.master_file), exist_ok=True)
        with open(self.master_file, 'w', encoding='utf-8') as f:
            f.write(final_content)

        logger.info(
            f"Assembly complete. Included: {stats['included']}, "
            f"Skipped: {stats['skipped']}, Output: {self.master_file}"
        )

        return stats

    def _assemble_from_files(
        self,
        files: List[Dict[str, Any]],
        source_dir: str,
        sort_by: str
    ) -> Dict[str, Any]:
        """Assemble from a specific source directory."""
        stats = {
            'total_files': len(files),
            'included': 0,
            'skipped': 0,
            'output_path': self.master_file
        }

        # Sort files
        sorted_files = self._sort_files(files, sort_by)

        # Prepare output
        master_content = []

        # Add header
        master_content.append(self._generate_header())

        # Add table of contents if enabled
        if self.include_toc:
            master_content.append(self._generate_toc(sorted_files))

        # Process each file
        for file_data in sorted_files:
            file_id = file_data['file_id']
            file_path = f"{source_dir}/{file_id}.md"

            if not os.path.exists(file_path):
                logger.warning(f"Markdown file not found: {file_path}")
                stats['skipped'] += 1
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Build document section
                section = self._build_document_section(file_data, content)
                master_content.append(section)
                stats['included'] += 1

            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
                stats['skipped'] += 1
                continue

        # Combine all content
        final_content = '\n'.join(master_content)

        # Save master file
        os.makedirs(os.path.dirname(self.master_file), exist_ok=True)
        with open(self.master_file, 'w', encoding='utf-8') as f:
            f.write(final_content)

        logger.info(
            f"Assembly complete. Included: {stats['included']}, "
            f"Skipped: {stats['skipped']}, Output: {self.master_file}"
        )

        return stats

    def _sort_files(
        self,
        files: List[Dict[str, Any]],
        sort_by: str
    ) -> List[Dict[str, Any]]:
        """Sort files according to specified criteria."""
        if sort_by == 'name':
            return sorted(files, key=lambda x: x.get('filename', ''))
        elif sort_by == 'date':
            return sorted(files, key=lambda x: x.get('last_processed', ''))
        elif sort_by == 'size':
            return sorted(files, key=lambda x: int(x.get('size_bytes', 0)), reverse=True)
        elif sort_by == 'type':
            return sorted(files, key=lambda x: (x.get('file_type', ''), x.get('filename', '')))
        else:  # default: path
            return sorted(files, key=lambda x: (x.get('source_path', ''), x.get('filename', '')))

    def _generate_header(self) -> str:
        """Generate header for master markdown file."""
        header = [
            "# Knowledge Base",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "This knowledge base was automatically generated from Google Drive content.",
            "",
        ]
        return '\n'.join(header)

    def _generate_toc(self, files: List[Dict[str, Any]]) -> str:
        """Generate table of contents."""
        toc = [
            "## Table of Contents",
            "",
        ]

        # Group by folder
        folders = {}
        for file_data in files:
            folder = file_data.get('source_path', '/')
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(file_data)

        # Generate TOC entries
        for folder in sorted(folders.keys()):
            folder_display = format_folder_path(folder, self.folder_separator)
            if folder_display:
                toc.append(f"### {folder_display}")
            else:
                toc.append("### Root")

            for file_data in folders[folder]:
                filename = file_data.get('filename', 'Unknown')
                # Create anchor link (simplified)
                anchor = self._create_anchor(folder, filename)
                toc.append(f"- [{filename}](#{anchor})")

            toc.append("")

        toc.append("")
        return '\n'.join(toc)

    def _create_anchor(self, folder: str, filename: str) -> str:
        """Create markdown anchor link."""
        # Combine folder and filename
        full_path = f"{folder}/{filename}"

        # Clean for anchor (lowercase, replace spaces/special chars with hyphens)
        anchor = full_path.lower()
        anchor = ''.join(c if c.isalnum() or c == '-' else '-' for c in anchor)
        anchor = '-'.join(filter(None, anchor.split('-')))  # Remove consecutive hyphens

        return anchor

    def _build_document_section(
        self,
        file_data: Dict[str, Any],
        content: str
    ) -> str:
        """Build a section for a single document."""
        section_parts = []

        # Add section separator
        section_parts.append(self.section_separator)

        # Build folder path for context
        folder_path = format_folder_path(
            file_data.get('source_path', '/'),
            self.folder_separator
        )

        # Add document header with folder context
        if folder_path:
            doc_header = f"# [{folder_path}] {file_data.get('filename', 'Unknown')}"
        else:
            doc_header = f"# {file_data.get('filename', 'Unknown')}"

        section_parts.append(doc_header)
        section_parts.append("")

        # Add metadata if enabled
        if self.include_metadata:
            metadata = self._generate_metadata(file_data)
            section_parts.append(metadata)

        # Add content
        section_parts.append(content)
        section_parts.append("")

        return '\n'.join(section_parts)

    def _generate_metadata(self, file_data: Dict[str, Any]) -> str:
        """Generate YAML frontmatter metadata."""
        metadata = [
            "---",
            f"file_id: {file_data.get('file_id', 'unknown')}",
            f"source_path: {file_data.get('source_path', '/')}",
            f"folder_path: {file_data.get('source_path', '/')}",
            f"original_filename: {file_data.get('filename', 'unknown')}",
            f"file_type: {file_data.get('file_type', 'unknown')}",
            f"mime_type: {file_data.get('mime_type', 'unknown')}",
        ]

        if file_data.get('size_bytes'):
            metadata.append(f"size_bytes: {file_data.get('size_bytes')}")

        if file_data.get('last_processed'):
            metadata.append(f"processed_date: {file_data.get('last_processed')}")

        metadata.append("---")
        metadata.append("")

        return '\n'.join(metadata)


def assemble_markdown(
    config: Config,
    inventory: InventoryManager,
    use_llm_processed: bool = True,
    sort_by: str = 'path'
) -> Dict[str, Any]:
    """
    Convenience function to assemble markdown files.

    Args:
        config: Configuration object
        inventory: Inventory manager
        use_llm_processed: Whether to use LLM-processed files
        sort_by: Sort order for files

    Returns:
        Assembly statistics
    """
    assembler = MarkdownAssembler(config, inventory)
    return assembler.assemble_knowledge_base(
        use_llm_processed=use_llm_processed,
        sort_by=sort_by
    )
