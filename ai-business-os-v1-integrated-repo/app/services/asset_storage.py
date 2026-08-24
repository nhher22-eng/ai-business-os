"""Storage abstraction for reusable image-element workflow records.

The first provider uses the persistent Docker media volume.  Storage keys are
provider-neutral so an S3 provider can be introduced without changing API or
database consumers.
"""

from __future__ import annotations

import json
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings


class StorageProvider(ABC):
    @abstractmethod
    def read_json(self, storage_key: str, default: dict | None = None) -> dict:
        raise NotImplementedError

    @abstractmethod
    def write_json(self, storage_key: str, value: dict) -> None:
        raise NotImplementedError


class LocalStorageProvider(StorageProvider):
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _path(self, storage_key: str) -> Path:
        key = storage_key.strip("/")
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("invalid storage key")
        return path

    def read_json(self, storage_key: str, default: dict | None = None) -> dict:
        path = self._path(storage_key)
        if not path.exists():
            return dict(default or {})
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, storage_key: str, value: dict) -> None:
        path = self._path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


class S3StorageProvider(StorageProvider):
    """Reserved provider boundary; activated after bucket migration settings."""

    def read_json(self, storage_key: str, default: dict | None = None) -> dict:
        raise RuntimeError("S3 storage provider is not configured")

    def write_json(self, storage_key: str, value: dict) -> None:
        raise RuntimeError("S3 storage provider is not configured")


def get_asset_storage() -> StorageProvider:
    if settings.asset_storage_provider.lower() == "local":
        return LocalStorageProvider(settings.asset_storage_root)
    if settings.asset_storage_provider.lower() == "s3":
        return S3StorageProvider()
    raise RuntimeError("unsupported asset storage provider")
