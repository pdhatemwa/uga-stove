import hashlib
import io
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

import boto3
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from api.config import get_settings

ALLOWED_IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png"}
ALLOWED_CONTENT_TYPES = {**ALLOWED_IMAGE_TYPES, "application/pdf": "pdf"}



@dataclass(frozen=True)
class StoredEvidence:
    object_key: str
    content_type: str
    size_bytes: int
    sha256: str
    original_filename: str


def _validated_bytes(upload: UploadFile, raw: bytes) -> tuple[bytes, str, str]:
    settings = get_settings()
    if len(raw) > settings.max_evidence_bytes:
        raise HTTPException(status_code=413, detail="Evidence file is too large")
    if not raw:
        raise HTTPException(status_code=400, detail="Evidence file is empty")
    claimed_type = (upload.content_type or "").lower()
    if claimed_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Use a JPEG, PNG, or PDF evidence file")

    if claimed_type in ALLOWED_IMAGE_TYPES:
        try:
            with Image.open(io.BytesIO(raw)) as image:
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                image = image.convert("RGB")
                clean = io.BytesIO()
                image.save(clean, format="JPEG", quality=90, optimize=True)
                raw = clean.getvalue()
            return raw, "image/jpeg", "jpg"
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(status_code=400, detail="The uploaded image is not valid") from exc

    if not raw.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded PDF is not valid")
    return raw, "application/pdf", "pdf"


class EvidenceStorage:
    def __init__(self):
        self.settings = get_settings()

    async def put(self, distribution_id: str, upload: UploadFile) -> StoredEvidence:
        raw = await upload.read(self.settings.max_evidence_bytes + 1)
        raw, content_type, extension = _validated_bytes(upload, raw)
        digest = hashlib.sha256(raw).hexdigest()
        object_key = f"signatures/{distribution_id}/{uuid.uuid4()}.{extension}"
        if self.settings.evidence_storage == "s3":
            self._put_s3(object_key, raw, content_type)
        else:
            self._put_local(object_key, raw)
        return StoredEvidence(
            object_key=object_key,
            content_type=content_type,
            size_bytes=len(raw),
            sha256=digest,
            original_filename=Path(upload.filename or f"evidence.{extension}").name[:255],
        )

    def get(self, object_key: str) -> bytes:
        if self.settings.evidence_storage == "s3":
            client = self._s3_client()
            response = client.get_object(Bucket=self.settings.s3_bucket, Key=object_key)
            return response["Body"].read()
        path = (self.settings.evidence_local_dir / object_key).resolve()
        root = self.settings.evidence_local_dir.resolve()
        if root not in path.parents:
            raise ValueError("Invalid evidence object key")
        return path.read_bytes()

    def _put_local(self, object_key: str, raw: bytes) -> None:
        path = (self.settings.evidence_local_dir / object_key).resolve()
        root = self.settings.evidence_local_dir.resolve()
        if root not in path.parents:
            raise ValueError("Invalid evidence object key")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(raw)
        os.replace(temporary, path)

    def _s3_client(self):
        if not self.settings.s3_bucket:
            raise RuntimeError("S3_BUCKET is required when EVIDENCE_STORAGE=s3")
        return boto3.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url,
            aws_access_key_id=self.settings.s3_access_key_id,
            aws_secret_access_key=self.settings.s3_secret_access_key,
            region_name=self.settings.s3_region,
        )

    def _put_s3(self, object_key: str, raw: bytes, content_type: str) -> None:
        self._s3_client().put_object(
            Bucket=self.settings.s3_bucket,
            Key=object_key,
            Body=raw,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )
