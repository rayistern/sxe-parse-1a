"""
Utility functions for Google Drive to Markdown processor.
Handles configuration loading, logging setup, and common helpers.
"""

import os
import csv
import logging
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv


class Config:
    """Configuration manager for the application."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        return config

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Path to config value (e.g., 'google_drive.folder_id')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value using dot notation.

        Args:
            key_path: Path to config value (e.g., 'llm.enabled')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value


def setup_logging(config: Config) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        config: Configuration object

    Returns:
        Configured logger
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Get logging configuration
    log_level = os.getenv('LOG_LEVEL', config.get('logging.level', 'INFO'))
    log_file = config.get('logging.file', 'logs/gdrive_processor.log')
    log_format = config.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    max_size_mb = config.get('logging.max_size_mb', 10)
    backup_count = config.get('logging.backup_count', 5)

    # Create logger
    logger = logging.getLogger('gdrive_processor')
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


class InventoryManager:
    """Manages the inventory CSV with versioning support."""

    FIELDNAMES = [
        'file_id',
        'source_path',
        'filename',
        'file_type',
        'size_bytes',
        'drive_file_id',
        'mime_type',
        'version',
        'status',
        'last_processed',
        'error_message'
    ]

    def __init__(self, inventory_path: str = "data/inventory.csv", enable_versioning: bool = True):
        self.inventory_path = inventory_path
        self.enable_versioning = enable_versioning
        self._ensure_inventory_exists()

    def _ensure_inventory_exists(self) -> None:
        """Create inventory CSV if it doesn't exist."""
        if not os.path.exists(self.inventory_path):
            os.makedirs(os.path.dirname(self.inventory_path), exist_ok=True)
            with open(self.inventory_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()

    def get_all_files(self) -> List[Dict[str, Any]]:
        """Get all files from inventory."""
        files = []
        with open(self.inventory_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                files.append(row)
        return files

    def get_latest_version(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest version of a file by file_id."""
        files = self.get_all_files()
        file_versions = [f for f in files if f['file_id'] == file_id]

        if not file_versions:
            return None

        # Sort by version (descending)
        file_versions.sort(key=lambda x: int(x.get('version', 0)), reverse=True)
        return file_versions[0]

    def get_next_file_id(self) -> str:
        """Get the next available file ID."""
        files = self.get_all_files()
        if not files:
            return "001"

        # Get all unique file IDs
        file_ids = list(set(f['file_id'] for f in files))

        # Find max and increment
        max_id = max(int(fid) for fid in file_ids if fid.isdigit())
        return f"{max_id + 1:03d}"

    def add_or_update_file(self, file_data: Dict[str, Any]) -> None:
        """
        Add a new file or create a new version of an existing file.

        Args:
            file_data: Dictionary containing file information
        """
        file_id = file_data.get('file_id')

        if self.enable_versioning:
            # Get current version
            latest = self.get_latest_version(file_id)
            if latest:
                version = int(latest.get('version', 0)) + 1
            else:
                version = 1

            file_data['version'] = version
        else:
            file_data['version'] = 1

        # Add timestamp
        file_data['last_processed'] = datetime.now().isoformat()

        # Append to CSV
        with open(self.inventory_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writerow(file_data)

    def get_files_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get files with a specific status (from latest versions only)."""
        files = self.get_all_files()

        # Group by file_id and get latest version
        latest_files = {}
        for file in files:
            file_id = file['file_id']
            if file_id not in latest_files:
                latest_files[file_id] = file
            else:
                current_version = int(latest_files[file_id].get('version', 0))
                new_version = int(file.get('version', 0))
                if new_version > current_version:
                    latest_files[file_id] = file

        # Filter by status
        return [f for f in latest_files.values() if f.get('status') == status]

    def get_pending_files(self, reprocess: bool = False) -> List[Dict[str, Any]]:
        """
        Get files that need processing.

        Args:
            reprocess: If True, include completed files for reprocessing

        Returns:
            List of files to process
        """
        files = self.get_all_files()

        # Group by file_id and get latest version
        latest_files = {}
        for file in files:
            file_id = file['file_id']
            if file_id not in latest_files:
                latest_files[file_id] = file
            else:
                current_version = int(latest_files[file_id].get('version', 0))
                new_version = int(file.get('version', 0))
                if new_version > current_version:
                    latest_files[file_id] = file

        if reprocess:
            return list(latest_files.values())
        else:
            return [f for f in latest_files.values() if f.get('status') != 'completed']


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe filesystem usage.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')

    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext

    return filename


def get_file_extension(filename: str) -> str:
    """
    Get file extension without the dot.

    Args:
        filename: Filename with extension

    Returns:
        Extension without dot (lowercase)
    """
    ext = os.path.splitext(filename)[1]
    return ext.lstrip('.').lower()


def format_folder_path(path: str, separator: str = " > ") -> str:
    """
    Format folder path with custom separator.

    Args:
        path: Original path
        separator: Separator to use

    Returns:
        Formatted path
    """
    # Remove leading/trailing slashes
    path = path.strip('/')

    # Split and rejoin with separator
    parts = path.split('/')
    return separator.join(parts) if parts else ""


def chunk_text(text: str, max_size: int, overlap: int = 0) -> List[str]:
    """
    Split text into chunks with optional overlap.

    Args:
        text: Text to split
        max_size: Maximum chunk size in characters
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= max_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_size

        # Try to break at a newline
        if end < len(text):
            newline_pos = text.rfind('\n', start, end)
            if newline_pos > start:
                end = newline_pos + 1

        chunks.append(text[start:end])
        start = end - overlap

    return chunks


def load_env() -> None:
    """Load environment variables from .env file."""
    load_dotenv()


def get_mime_type_category(mime_type: str) -> str:
    """
    Categorize MIME type into general categories.

    Args:
        mime_type: MIME type string

    Returns:
        Category: document, spreadsheet, image, audio, video, archive, or other
    """
    mime_map = {
        'application/vnd.google-apps.document': 'google_doc',
        'application/vnd.google-apps.spreadsheet': 'google_sheet',
        'application/vnd.google-apps.presentation': 'google_slide',
        'application/pdf': 'document',
        'application/msword': 'document',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'document',
        'application/vnd.oasis.opendocument.text': 'document',
        'text/plain': 'document',
        'text/html': 'document',
        'text/markdown': 'document',
        'application/vnd.ms-excel': 'spreadsheet',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'spreadsheet',
        'text/csv': 'spreadsheet',
        'image/': 'image',
        'audio/': 'audio',
        'video/': 'video',
        'application/zip': 'archive',
        'application/x-rar': 'archive',
        'application/x-7z': 'archive',
    }

    for key, value in mime_map.items():
        if mime_type.startswith(key):
            return value

    return 'other'
