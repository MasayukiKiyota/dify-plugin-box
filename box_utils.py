"""
Box utilities module.
Contains common functionality used across Box tools.

Box works with numeric IDs rather than paths: the root folder is always "0",
and files/folders are addressed by their ID. These helpers wrap the Box
Content API (https://api.box.com/2.0) and its upload host
(https://upload.box.com/api/2.0).
"""
import json
import mimetypes
from typing import Any, Optional

import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BoxApiError(Exception):
    """Raised when the Box API returns an error response."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class BoxUtils:
    """Utilities for Box operations."""

    API_BASE_URL = "https://api.box.com/2.0"
    UPLOAD_BASE_URL = "https://upload.box.com/api/2.0"
    ROOT_FOLDER_ID = "0"

    @staticmethod
    def _session() -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.verify = certifi.where()
        return session

    @staticmethod
    def _auth_headers(access_token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {access_token}"}

    @staticmethod
    def _raise_for_status(response: requests.Response, action: str) -> None:
        if response.status_code == 401:
            raise BoxApiError(
                "Authentication failed (401 Unauthorized). The access token may have "
                "expired. Please refresh or re-authorize the connection.",
                status_code=401,
            )
        if response.status_code == 404:
            raise BoxApiError(f"Not found while trying to {action}.", status_code=404)
        if response.status_code == 409:
            raise BoxApiError(
                f"A conflict occurred while trying to {action} (item may already exist).",
                status_code=409,
            )
        if not response.ok:
            raise BoxApiError(
                f"Error while trying to {action}: {response.status_code} - {response.text[:300]}",
                status_code=response.status_code,
            )

    @staticmethod
    def _format_entry(entry: dict[str, Any]) -> dict[str, Any]:
        item = {
            "id": entry.get("id"),
            "name": entry.get("name"),
            "type": entry.get("type"),
        }
        if entry.get("type") == "file":
            item["size"] = entry.get("size")
        if entry.get("modified_at"):
            item["modified"] = entry.get("modified_at")
        return item

    @staticmethod
    def list_folder(access_token: str, folder_id: str = "0", limit: int = 100) -> list[dict[str, Any]]:
        """
        List the items inside a Box folder.

        Args:
            access_token: Box OAuth access token
            folder_id: The Box folder ID ("0" is the root folder)
            limit: Maximum number of items to return

        Returns:
            List of dictionaries describing each file/folder.
        """
        folder_id = folder_id or BoxUtils.ROOT_FOLDER_ID
        session = BoxUtils._session()
        url = f"{BoxUtils.API_BASE_URL}/folders/{folder_id}/items"
        params = {"limit": limit, "fields": "id,name,size,type,modified_at"}

        response = session.get(
            url, headers=BoxUtils._auth_headers(access_token), params=params, timeout=30
        )
        BoxUtils._raise_for_status(response, f"list folder '{folder_id}'")

        entries = response.json().get("entries", [])
        return [BoxUtils._format_entry(entry) for entry in entries]

    @staticmethod
    def search(access_token: str, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """
        Search for files and folders in Box.

        Args:
            access_token: Box OAuth access token
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of dictionaries describing each match.
        """
        session = BoxUtils._session()
        url = f"{BoxUtils.API_BASE_URL}/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "id,name,size,type,modified_at",
        }

        response = session.get(
            url, headers=BoxUtils._auth_headers(access_token), params=params, timeout=30
        )
        BoxUtils._raise_for_status(response, f"search for '{query}'")

        entries = response.json().get("entries", [])
        return [BoxUtils._format_entry(entry) for entry in entries]

    @staticmethod
    def upload_file(
        access_token: str,
        file_name: str,
        content: bytes,
        parent_folder_id: str = "0",
    ) -> dict[str, Any]:
        """
        Upload a new file to Box.

        Args:
            access_token: Box OAuth access token
            file_name: Name of the file to create in Box
            content: File content as bytes
            parent_folder_id: The destination folder ID ("0" is the root folder)

        Returns:
            Dictionary describing the uploaded file.
        """
        parent_folder_id = parent_folder_id or BoxUtils.ROOT_FOLDER_ID
        session = BoxUtils._session()
        url = f"{BoxUtils.UPLOAD_BASE_URL}/files/content"

        attributes = {"name": file_name, "parent": {"id": parent_folder_id}}
        files = {
            "attributes": (None, json.dumps(attributes), "application/json"),
            "file": (file_name, content),
        }

        response = session.post(
            url, headers=BoxUtils._auth_headers(access_token), files=files, timeout=120
        )
        BoxUtils._raise_for_status(response, f"upload file '{file_name}'")

        entries = response.json().get("entries", [])
        if not entries:
            raise BoxApiError(f"Upload of '{file_name}' returned no file entry.")
        return BoxUtils._format_entry(entries[0])

    @staticmethod
    def download_file(access_token: str, file_id: str) -> dict[str, Any]:
        """
        Download a file's content and metadata from Box.

        Args:
            access_token: Box OAuth access token
            file_id: The Box file ID

        Returns:
            Dictionary with the file content (bytes) and metadata.
        """
        session = BoxUtils._session()
        headers = BoxUtils._auth_headers(access_token)

        # Fetch metadata first so we can report name/size.
        meta_url = f"{BoxUtils.API_BASE_URL}/files/{file_id}"
        meta_response = session.get(
            meta_url, headers=headers, params={"fields": "id,name,size,type,modified_at"}, timeout=30
        )
        BoxUtils._raise_for_status(meta_response, f"get metadata for file '{file_id}'")
        metadata = meta_response.json()

        if metadata.get("type") == "folder":
            raise BoxApiError(f"Cannot download folder '{metadata.get('name')}'. Please select a file.")

        # Download the actual content.
        content_url = f"{BoxUtils.API_BASE_URL}/files/{file_id}/content"
        content_response = session.get(content_url, headers=headers, timeout=120, stream=True)
        BoxUtils._raise_for_status(content_response, f"download file '{file_id}'")

        return {
            "id": metadata.get("id"),
            "name": metadata.get("name"),
            "size": metadata.get("size"),
            "modified": metadata.get("modified_at"),
            "content": content_response.content,
            "mime_type": BoxUtils.guess_mime_type(metadata.get("name", "")),
        }

    @staticmethod
    def create_folder(access_token: str, name: str, parent_folder_id: str = "0") -> dict[str, Any]:
        """
        Create a new folder in Box.

        Args:
            access_token: Box OAuth access token
            name: Name of the new folder
            parent_folder_id: The parent folder ID ("0" is the root folder)

        Returns:
            Dictionary describing the created folder.
        """
        parent_folder_id = parent_folder_id or BoxUtils.ROOT_FOLDER_ID
        session = BoxUtils._session()
        url = f"{BoxUtils.API_BASE_URL}/folders"
        payload = {"name": name, "parent": {"id": parent_folder_id}}
        headers = {**BoxUtils._auth_headers(access_token), "Content-Type": "application/json"}

        response = session.post(url, headers=headers, json=payload, timeout=30)
        BoxUtils._raise_for_status(response, f"create folder '{name}'")

        return BoxUtils._format_entry(response.json())

    @staticmethod
    def delete_item(access_token: str, item_id: str, is_folder: bool = False) -> dict[str, Any]:
        """
        Delete a file or folder from Box.

        Args:
            access_token: Box OAuth access token
            item_id: The Box file or folder ID
            is_folder: Whether the item is a folder (deleted recursively)

        Returns:
            Dictionary confirming the deletion.
        """
        session = BoxUtils._session()
        if is_folder:
            url = f"{BoxUtils.API_BASE_URL}/folders/{item_id}"
            params = {"recursive": "true"}
        else:
            url = f"{BoxUtils.API_BASE_URL}/files/{item_id}"
            params = {}

        response = session.delete(
            url, headers=BoxUtils._auth_headers(access_token), params=params, timeout=30
        )
        BoxUtils._raise_for_status(response, f"delete item '{item_id}'")

        return {
            "id": item_id,
            "type": "folder" if is_folder else "file",
            "status": "deleted",
        }

    @staticmethod
    def guess_mime_type(filename: str) -> str:
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"
