from abc import ABC, abstractmethod
from typing import BinaryIO, Optional, Union

from fnrgbookinventory.gcp_services.models_services.file_storage_models import FileObject, ListFilesResult, UploadOptions


class AbstractStorageService(ABC):

    @abstractmethod
    def upload_file(
        self,
        key: str,
        body: Union[bytes, BinaryIO, str],
        options: Optional[UploadOptions] = None,
    ) -> str:
        """Upload/overwrite a file at `key`. Returns the key on success."""
        raise NotImplementedError

    @abstractmethod
    def get_file(self, key: str) -> bytes:
        """Download a file's raw bytes."""
        raise NotImplementedError

    @abstractmethod
    def download_to_path(self, key: str, local_path: str) -> None:
        """Download a file directly to a local filesystem path (streamed)."""
        raise NotImplementedError

    @abstractmethod
    def delete_file(self, key: str) -> None:
        """Delete a single file."""
        raise NotImplementedError

    @abstractmethod
    def delete_files(self, keys: list[str]) -> None:
        """Delete multiple files in one batch call."""
        raise NotImplementedError

    @abstractmethod
    def list_files(
        self,
        prefix: Optional[str] = None,
        max_keys: int = 1000,
        continuation_token: Optional[str] = None,
    ) -> ListFilesResult:
        """List files, optionally filtered by prefix, with pagination support."""
        raise NotImplementedError

    @abstractmethod
    def file_exists(self, key: str) -> bool:
        """Check whether a file exists without downloading it."""
        raise NotImplementedError

    @abstractmethod
    def get_file_metadata(self, key: str) -> FileObject:
        """Get metadata (size, last modified, etag) without downloading the body."""
        raise NotImplementedError

    @abstractmethod
    def copy_file(self, source_key: str, destination_key: str) -> None:
        """Copy a file within the same bucket."""
        raise NotImplementedError

    @abstractmethod
    def get_signed_download_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        """Generate a time-limited signed URL for downloading a private file."""
        raise NotImplementedError

    @abstractmethod
    def get_signed_upload_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        """Generate a time-limited signed URL for uploading directly from a client."""
        raise NotImplementedError

    @abstractmethod
    def get_public_url(self, key: str) -> str:
        """Get a permanent public URL, if the bucket/domain is public."""
        raise NotImplementedError