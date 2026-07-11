from typing import Iterator

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .config import settings


def job_key(user_id: str, job_id: str, *parts: str) -> str:
    return "/".join(["users", user_id, "jobs", job_id, *parts])


class Storage:
    def __init__(self, endpoint: str | None, access_key: str, secret_key: str, bucket: str):
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
            config=Config(s3={"addressing_style": "path"}),
        )

    @classmethod
    def from_settings(cls) -> "Storage":
        return cls(
            endpoint=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket=settings.s3_bucket,
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> None:
        extra = {"ContentType": content_type} if content_type else {}
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra)

    def get_bytes(self, key: str) -> bytes:
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            raise KeyError(key) from e
        return resp["Body"].read()

    def head(self, key: str) -> int:
        try:
            resp = self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            raise KeyError(key) from e
        return int(resp["ContentLength"])

    def stream(
        self,
        key: str,
        start: int | None = None,
        end: int | None = None,
        chunk_size: int = 1024 * 1024,
    ) -> Iterator[bytes]:
        kwargs = {"Bucket": self.bucket, "Key": key}
        if start is not None:
            kwargs["Range"] = f"bytes={start}-{'' if end is None else end}"
        try:
            resp = self.client.get_object(**kwargs)
        except ClientError as e:
            raise KeyError(key) from e
        yield from resp["Body"].iter_chunks(chunk_size)

    def delete_prefix(self, prefix: str) -> None:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            contents = page.get("Contents", [])
            if contents:
                self.client.delete_objects(
                    Bucket=self.bucket,
                    Delete={"Objects": [{"Key": o["Key"]} for o in contents]},
                )
