import pytest
from fastapi import HTTPException

from app.api.canva_controlled_export import CanvaV12AutofillRequest, start_product_v12_autofill
from app.services import canva_connect


def test_autofill_request_uses_brand_template_and_94_data(monkeypatch):
    captured = {}
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"job": {"id": "job", "status": "in_progress"}}
    def post(url, **kwargs): captured.update(url=url, **kwargs); return Response()
    monkeypatch.setattr(canva_connect.httpx, "post", post)
    data = {f"field_{i}": {"type": "text", "text": "x"} for i in range(94)}
    canva_connect.create_autofill("token", template_id="EAHTvwXU8Ig", data=data, title="상품")
    assert captured["json"]["type"] == "create_from_brand_template"
    assert captured["json"]["brand_template_id"] == "EAHTvwXU8Ig"
    assert len(captured["json"]["data"]) == 94


def test_autofill_start_requires_explicit_approval():
    with pytest.raises(HTTPException) as exc:
        start_product_v12_autofill("p", CanvaV12AutofillRequest(), tenant_id="t", db=None)
    assert exc.value.status_code == 409
