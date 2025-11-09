"""
Google Drive file discovery module.
Lists all files from Google Drive and populates the inventory.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

from utils import Config, InventoryManager, get_mime_type_category, get_file_extension

logger = logging.getLogger('gdrive_processor.discovery')

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class GoogleDriveDiscovery:
    """Handles Google Drive file discovery and listing."""

    def __init__(self, config: Config, inventory: InventoryManager):
        self.config = config
        self.inventory = inventory
        self.service = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Google Drive API."""
        creds = None
        token_path = self.config.get('google_drive.token_path', 'token.json')
        credentials_path = self.config.get('google_drive.credentials_path', 'credentials.json')

        # Load existing token if available
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Google Drive credentials...")
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(
                        f"Google credentials file not found: {credentials_path}\n"
                        "Please download credentials.json from Google Cloud Console."
                    )

                logger.info("Initiating Google Drive authentication flow...")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next time
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        # Build service
        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Successfully authenticated with Google Drive")

    def list_all_files(
        self,
        folder_id: Optional[str] = None,
        include_shared_drives: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all files from Google Drive.

        Args:
            folder_id: Optional folder ID to start from
            include_shared_drives: Whether to include shared drives

        Returns:
            List of file metadata dictionaries
        """
        all_files = []

        try:
            # Build query
            if folder_id:
                query = f"'{folder_id}' in parents"
            else:
                query = None

            # Get skip extensions from config
            skip_extensions = self.config.get('file_types.skip_extensions', [])

            # Recursively list files
            files = self._list_files_recursive(
                query=query,
                include_shared_drives=include_shared_drives,
                skip_extensions=skip_extensions
            )

            all_files.extend(files)

            logger.info(f"Discovered {len(all_files)} files from Google Drive")

        except HttpError as error:
            logger.error(f"An error occurred during discovery: {error}")
            raise

        return all_files

    def _list_files_recursive(
        self,
        query: Optional[str] = None,
        include_shared_drives: bool = False,
        skip_extensions: List[str] = None,
        parent_path: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Recursively list files from Google Drive.

        Args:
            query: Query string for filtering
            include_shared_drives: Whether to include shared drives
            skip_extensions: List of extensions to skip
            parent_path: Current parent path for building full paths

        Returns:
            List of file metadata
        """
        files = []
        page_token = None
        skip_extensions = skip_extensions or []

        while True:
            try:
                # List files
                results = self.service.files().list(
                    q=query,
                    pageSize=1000,
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents, webViewLink)",
                    pageToken=page_token,
                    supportsAllDrives=include_shared_drives,
                    includeItemsFromAllDrives=include_shared_drives
                ).execute()

                items = results.get('files', [])

                for item in items:
                    mime_type = item.get('mimeType', '')
                    name = item.get('name', '')

                    # Build full path
                    current_path = f"{parent_path}/{name}" if parent_path else f"/{name}"

                    # Check if it's a folder
                    if mime_type == 'application/vnd.google-apps.folder':
                        # Recursively process folder
                        folder_query = f"'{item['id']}' in parents"
                        subfolder_files = self._list_files_recursive(
                            query=folder_query,
                            include_shared_drives=include_shared_drives,
                            skip_extensions=skip_extensions,
                            parent_path=current_path
                        )
                        files.extend(subfolder_files)
                        continue

                    # Skip files with ignored extensions
                    extension = get_file_extension(name)
                    if extension in skip_extensions:
                        logger.debug(f"Skipping file with ignored extension: {current_path}")
                        continue

                    # Add file metadata
                    file_data = {
                        'drive_file_id': item.get('id'),
                        'filename': name,
                        'source_path': os.path.dirname(current_path),
                        'mime_type': mime_type,
                        'size_bytes': int(item.get('size', 0)) if item.get('size') else 0,
                        'modified_time': item.get('modifiedTime'),
                        'web_view_link': item.get('webViewLink'),
                        'file_type': get_mime_type_category(mime_type)
                    }

                    files.append(file_data)

                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            except HttpError as error:
                logger.error(f"Error listing files: {error}")
                raise

        return files

    def populate_inventory(
        self,
        folder_id: Optional[str] = None,
        include_shared_drives: bool = False
    ) -> int:
        """
        Discover files and populate inventory.

        Args:
            folder_id: Optional folder ID to start from
            include_shared_drives: Whether to include shared drives

        Returns:
            Number of files added to inventory
        """
        logger.info("Starting file discovery...")

        # Get folder ID from config if not provided
        if folder_id is None:
            folder_id = self.config.get('google_drive.folder_id', None)
            if not folder_id:
                folder_id = None  # Process entire drive

        # Get shared drives setting from config
        if include_shared_drives is None:
            include_shared_drives = self.config.get('google_drive.include_shared_drives', False)

        # List all files
        files = self.list_all_files(
            folder_id=folder_id,
            include_shared_drives=include_shared_drives
        )

        # Get existing files from inventory
        existing_files = {f['drive_file_id']: f for f in self.inventory.get_all_files()}

        # Track new files
        new_count = 0

        for file_data in files:
            drive_id = file_data['drive_file_id']

            # Check if file already exists in inventory
            if drive_id in existing_files:
                logger.debug(f"File already in inventory: {file_data['filename']}")
                continue

            # Get next file ID
            file_id = self.inventory.get_next_file_id()

            # Prepare inventory entry
            inventory_entry = {
                'file_id': file_id,
                'source_path': file_data['source_path'],
                'filename': file_data['filename'],
                'file_type': file_data['file_type'],
                'size_bytes': file_data['size_bytes'],
                'drive_file_id': file_data['drive_file_id'],
                'mime_type': file_data['mime_type'],
                'status': 'pending',
                'error_message': ''
            }

            # Add to inventory
            self.inventory.add_or_update_file(inventory_entry)
            new_count += 1

            logger.debug(f"Added to inventory: {file_id} - {file_data['source_path']}/{file_data['filename']}")

        logger.info(f"Discovery complete. Added {new_count} new files to inventory.")
        return new_count


def discover_files(config: Config, inventory: InventoryManager, folder_id: Optional[str] = None) -> int:
    """
    Convenience function to discover files and populate inventory.

    Args:
        config: Configuration object
        inventory: Inventory manager
        folder_id: Optional folder ID to start from

    Returns:
        Number of new files discovered
    """
    discovery = GoogleDriveDiscovery(config, inventory)
    return discovery.populate_inventory(folder_id=folder_id)
