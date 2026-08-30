import base64

import pytest
from fastapi import HTTPException

from app.api.canva_controlled_export import CanvaV12CanvaUploadRequest, upload_product_v12_images_to_canva
from app.services import canva_connect


def test_asset_upload_uses_binary_body_and_base64_name(monkeypatch):
    captured = {}
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"job": {"id": "job-1", "status": "in_progress"}}
    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs); return Response()
    monkeypatch.setattr(canva_connect.httpx, "post", fake_post)
    result = canva_connect.create_asset_upload("token", content=b"image", name="관수키트.png")
    assert result["job"]["id"] == "job-1"
    assert captured["content"] == b"image"
    assert captured["headers"]["Content-Type"] == "application/octet-stream"
    assert base64.b64encode("관수키트.png".encode()).decode() in captured["headers"]["Asset-Upload-Metadata"]


def test_canva_upload_requires_explicit_execution_approval():
    with pytest.raises(HTTPException) as exc:
        upload_product_v12_images_to_canva("product", CanvaV12CanvaUploadRequest(), tenant_id="tenant", db=None)
    assert exc.value.status_code == 409
    assert "explicit" in exc.value.detail
