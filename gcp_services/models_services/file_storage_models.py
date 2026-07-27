
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime



@dataclass
class R2Config:
    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    public_url: Optional[str] = None 


@dataclass
class UploadOptions:
    content_type: Optional[str] = None
    metadata: Optional[dict] = None
    cache_control: Optional[str] = None


@dataclass
class FileObject:
    key: str
    size: int
    last_modified: Optional[datetime] = None
    etag: Optional[str] = None


@dataclass
class ListFilesResult:
    files: list[FileObject] = field(default_factory=list)
    is_truncated: bool = False
    next_continuation_token: Optional[str] = None