from __future__ import annotations
from ...app_shared.enums import R2ClientDefaults, S3ErrorCode, boto3_enums
from ...gcp_services.models_services.file_storage_models import FileObject, R2Config, UploadOptions
from ...utils.keys import get_env_value
from ...utils.r2_config import load_r2_config_from_env
from ..contracts.abstract_storage_service import AbstractStorageService
from ..models_services.file_storage_models import ListFilesResult

import os
from typing import BinaryIO, Optional, Union
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError





class CloudflareR2Service(AbstractStorageService):
    def __init__(self, config: R2Config):
        self.bucket_name = config.bucket_name

        self.client = boto3.client(
            R2ClientDefaults.SERVICE_NAME.value,
            endpoint_url=get_env_value(boto3_enums.END_POINT_URL),
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            config=Config(signature_version=R2ClientDefaults.SIGNATURE_VERSION.value),
            region_name=R2ClientDefaults.REGION.value,
        )

    @classmethod
    def from_env(cls) -> "CloudflareR2Service":
        """Convenience factory that reads config from environment variables."""
        return cls(load_r2_config_from_env())

    def upload_file(
        self,
        key: str,
        body: Union[bytes, BinaryIO, str],
        options: Optional[UploadOptions] = None,
    ) -> str:
        options = options or UploadOptions()

        extra_args = {}
        if options.content_type:
            extra_args["ContentType"] = options.content_type
        if options.metadata:
            extra_args["Metadata"] = options.metadata
        if options.cache_control:
            extra_args["CacheControl"] = options.cache_control

        if isinstance(body, str):
            body = body.encode("utf-8")

        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=body,
            **extra_args,
        )
        return key

    def get_file(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket_name, Key=key)
        return response["Body"].read()

    def download_to_path(self, key: str, local_path: str) -> None:
        self.client.download_file(self.bucket_name, key, local_path)

    def delete_file(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=key)

    def delete_files(self, keys: list[str]) -> None:
        if not keys:
            return

        # R2/S3 batch delete supports up to 1000 keys per request
        batch_size = 1000
        for i in range(0, len(keys), batch_size):
            batch = keys[i : i + batch_size]
            self.client.delete_objects(
                Bucket=self.bucket_name,
                Delete={"Objects": [{"Key": k} for k in batch]},
            )

    def list_files(
        self,
        prefix: Optional[str] = None,
        max_keys: int = 1000,
        continuation_token: Optional[str] = None,
    ) -> ListFilesResult:
        kwargs = {"Bucket": self.bucket_name, "MaxKeys": max_keys}
        if prefix:
            kwargs["Prefix"] = prefix
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        response = self.client.list_objects_v2(**kwargs)

        files = [
            FileObject(
                key=obj["Key"],
                size=obj["Size"],
                last_modified=obj.get("LastModified"),
                etag=obj.get("ETag"),
            )
            for obj in response.get("Contents", [])
        ]

        return ListFilesResult(
            files=files,
            is_truncated=response.get("IsTruncated", False),
            next_continuation_token=response.get("NextContinuationToken"),
        )

    def file_exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as err:
            error_code = err.response["Error"]["Code"]
            known_not_found_codes = {code.value for code in (
                S3ErrorCode.NOT_FOUND,
                S3ErrorCode.NO_SUCH_KEY,
                S3ErrorCode.NOT_FOUND_NAME,
            )}
            if error_code in known_not_found_codes:
                return False
            raise

    def get_file_metadata(self, key: str) -> FileObject:
        response = self.client.head_object(Bucket=self.bucket_name, Key=key)
        return FileObject(
            key=key,
            size=response.get("ContentLength", 0),
            last_modified=response.get("LastModified"),
            etag=response.get("ETag"),
        )

    def copy_file(self, source_key: str, destination_key: str) -> None:
        self.client.copy_object(
            Bucket=self.bucket_name,
            CopySource={"Bucket": self.bucket_name, "Key": source_key},
            Key=destination_key,
        )

    def get_signed_download_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in_seconds,
        )

    def get_signed_upload_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in_seconds,
        )

    def get_public_url(self, key: str) -> str:
        if not self.public_url:
            raise ValueError(
                "public_url was not configured. Set R2_PUBLIC_URL or pass "
                "public_url in R2Config, or use get_signed_download_url() instead."
            )
        return f"{self.public_url.rstrip('/')}/{key}"





# if __name__ == "__main__":
#     # Option 1: build config explicitly via the util, then construct the service
#     config = load_r2_config_from_env()
#     r2 = CloudflareR2Service(config)
 
#     # # Option 2: shortcut that does the same thing internally
#     # r2 = CloudflareR2Service.from_env()
 
#     # local_path = r"C:\Users\Dell\Downloads\IDA-SGA--1.pdf"

#     # with open(local_path, "rb") as f:
#     #         file_bytes = f.read()

#     # r2.upload_file(
#     #     "documents/IDA-SGA--1.pdf",   # this is the R2 object key — choose your own path/name
#     #     file_bytes,
#     #     UploadOptions(content_type="application/pdf"),
#     # )

#     # # Get
#     # data = r2.get_file(r"C:\Users\Dell\Downloads\IDA-SGA--1.pdf")
 
#     # # Delete
#     r2.delete_file(r"documents/IDA-SGA--1.pdf")
 
#     # # List
#     # result = r2.list_files(prefix="uploads/")
#     # for f in result.files:
#     #     print(f.key, f.size)
 
#     # # Signed URL for a private file
#     # url = r2.get_signed_download_url(r"C:\Users\Dell\Downloads\IDA-SGA--1.pdf", expires_in_seconds=900)
#     # print(url)