"""
Google Drive file download and export module.
Downloads regular files and exports Google Drive native formats.
"""

import os
import io
import logging
from typing import Dict, Optional, Any
from pathlib import Path
import pickle

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from utils import Config, InventoryManager, sanitize_filename

logger = logging.getLogger('gdrive_processor.download')

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Export MIME types for Google Drive native formats
EXPORT_MIME_TYPES = {
    'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # docx
    'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # xlsx
    'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # pptx
    'application/vnd.google-apps.drawing': 'application/pdf',
}

EXPORT_EXTENSIONS = {
    'application/vnd.google-apps.document': '.docx',
    'application/vnd.google-apps.spreadsheet': '.xlsx',
    'application/vnd.google-apps.presentation': '.pptx',
    'application/vnd.google-apps.drawing': '.pdf',
}


class GoogleDriveDownloader:
    """Handles downloading files from Google Drive."""

    def __init__(self, config: Config, inventory: InventoryManager):
        self.config = config
        self.inventory = inventory
        self.service = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Google Drive API."""
        token_path = self.config.get('google_drive.token_path', 'token.json')

        if not os.path.exists(token_path):
            raise FileNotFoundError(
                "Token file not found. Please run discovery first to authenticate."
            )

        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Successfully authenticated with Google Drive for downloads")

    def download_file(
        self,
        file_id: str,
        drive_file_id: str,
        filename: str,
        mime_type: str,
        output_dir: str = "data/raw"
    ) -> Optional[str]:
        """
        Download a file from Google Drive.

        Args:
            file_id: Internal file ID (from inventory)
            drive_file_id: Google Drive file ID
            filename: Original filename
            mime_type: File MIME type
            output_dir: Directory to save downloaded files

        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)

            # Check if it's a Google Drive native format
            if mime_type in EXPORT_MIME_TYPES:
                return self._export_google_file(
                    file_id,
                    drive_file_id,
                    filename,
                    mime_type,
                    output_dir
                )
            else:
                return self._download_regular_file(
                    file_id,
                    drive_file_id,
                    filename,
                    output_dir
                )

        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return None

    def _download_regular_file(
        self,
        file_id: str,
        drive_file_id: str,
        filename: str,
        output_dir: str
    ) -> Optional[str]:
        """Download a regular file (non-Google format)."""
        try:
            # Sanitize filename
            safe_filename = sanitize_filename(filename)
            file_extension = os.path.splitext(safe_filename)[1]

            # Build output path using file_id
            output_filename = f"{file_id}{file_extension}"
            output_path = os.path.join(output_dir, output_filename)

            # Download file
            request = self.service.files().get_media(fileId=drive_file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Download progress: {int(status.progress() * 100)}%")

            # Write to file
            with open(output_path, 'wb') as f:
                f.write(fh.getvalue())

            logger.info(f"Downloaded: {output_filename} ({filename})")
            return output_path

        except HttpError as error:
            logger.error(f"HTTP error downloading {file_id}: {error}")
            return None
        except Exception as error:
            logger.error(f"Error downloading {file_id}: {error}")
            return None

    def _export_google_file(
        self,
        file_id: str,
        drive_file_id: str,
        filename: str,
        mime_type: str,
        output_dir: str
    ) -> Optional[str]:
        """Export a Google Drive native format file."""
        try:
            # Get export MIME type and extension
            export_mime_type = EXPORT_MIME_TYPES.get(mime_type)
            export_extension = EXPORT_EXTENSIONS.get(mime_type)

            if not export_mime_type or not export_extension:
                logger.warning(f"No export format defined for {mime_type}")
                return None

            # Build output path
            output_filename = f"{file_id}{export_extension}"
            output_path = os.path.join(output_dir, output_filename)

            # Export file
            request = self.service.files().export_media(
                fileId=drive_file_id,
                mimeType=export_mime_type
            )

            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Export progress: {int(status.progress() * 100)}%")

            # Write to file
            with open(output_path, 'wb') as f:
                f.write(fh.getvalue())

            logger.info(f"Exported: {output_filename} ({filename})")
            return output_path

        except HttpError as error:
            logger.error(f"HTTP error exporting {file_id}: {error}")
            return None
        except Exception as error:
            logger.error(f"Error exporting {file_id}: {error}")
            return None

    def download_pending_files(self, max_files: Optional[int] = None) -> Dict[str, Any]:
        """
        Download all pending files from inventory.

        Args:
            max_files: Optional limit on number of files to download

        Returns:
            Dictionary with download statistics
        """
        # Get pending files
        pending = self.inventory.get_pending_files()

        if max_files:
            pending = pending[:max_files]

        stats = {
            'total': len(pending),
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        logger.info(f"Starting download of {len(pending)} files...")

        for file_data in pending:
            file_id = file_data['file_id']
            drive_file_id = file_data['drive_file_id']
            filename = file_data['filename']
            mime_type = file_data['mime_type']

            logger.info(f"Processing {file_id}: {filename}")

            # Download file
            output_path = self.download_file(
                file_id,
                drive_file_id,
                filename,
                mime_type
            )

            if output_path:
                # Update inventory
                file_data['status'] = 'downloaded'
                file_data['error_message'] = ''
                self.inventory.add_or_update_file(file_data)
                stats['success'] += 1
            else:
                # Mark as failed
                file_data['status'] = 'download_failed'
                file_data['error_message'] = 'Download failed'
                self.inventory.add_or_update_file(file_data)
                stats['failed'] += 1

        logger.info(
            f"Download complete. Success: {stats['success']}, "
            f"Failed: {stats['failed']}"
        )

        return stats


def download_files(
    config: Config,
    inventory: InventoryManager,
    max_files: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function to download files.

    Args:
        config: Configuration object
        inventory: Inventory manager
        max_files: Optional limit on number of files

    Returns:
        Download statistics
    """
    downloader = GoogleDriveDownloader(config, inventory)
    return downloader.download_pending_files(max_files=max_files)
