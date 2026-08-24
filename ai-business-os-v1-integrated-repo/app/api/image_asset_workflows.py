from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.asset_storage import get_asset_storage


router = APIRouter(prefix="/api/v1/image-asset-workflows", tags=["image-asset-workflows"])


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def key(tenant_id: str, product_id: str) -> str:
    safe = lambda value: "".join(ch for ch in value if ch.isalnum() or ch in "-_")
    return f"image-elements/{safe(tenant_id)}/{safe(product_id)}/workflow.json"


class WorkflowPlan(BaseModel):
    product_id: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    elements: list[dict[str, Any]] = Field(default_factory=list)
    quality: str = "standard"
    resolution: str = "web"
    budget_cap: int = 0
    estimated_cost: int = 0


@router.get("/{product_id}")
def get_workflow(product_id: str, tenant_id: str):
    return get_asset_storage().read_json(key(tenant_id, product_id), {"product_id": product_id, "status": "draft"})


@router.put("/{product_id}")
def save_workflow(product_id: str, payload: WorkflowPlan, tenant_id: str):
    if payload.product_id != product_id:
        raise HTTPException(400, "product id mismatch")
    current = get_asset_storage().read_json(key(tenant_id, product_id), {})
    value = payload.model_dump()
    value.update({"status": "draft", "updated_at": now(), "execution": current.get("execution")})
    get_asset_storage().write_json(key(tenant_id, product_id), value)
    return value


@router.post("/{product_id}/execute")
def execute_workflow(product_id: str, payload: WorkflowPlan, tenant_id: str):
    if payload.product_id != product_id:
        raise HTTPException(400, "product id mismatch")
    canonical = payload.model_dump_json(exclude={"budget_cap"})
    plan_hash = sha256(canonical.encode()).hexdigest()
    current = get_asset_storage().read_json(key(tenant_id, product_id), {})
    execution = current.get("execution") or {}
    if execution.get("plan_hash") == plan_hash:
        return current
    results = []
    for element in payload.elements:
        if not element.get("selected") or not element.get("ready"):
            continue
        derived = element.get("mode") == "derived"
        results.append({
            "element_code": element.get("code"),
            "name": element.get("name"),
            "status": "production_queued" if derived else "source_ready",
            "preview_url": element.get("preview_url"),
            "message": "기존 이미지 생성기 제작 대기" if derived else "주 원본 기준 보정 제작 대기",
        })
    value = payload.model_dump()
    value.update({
        "status": "executing",
        "updated_at": now(),
        "execution": {"plan_hash": plan_hash, "approved_at": now(), "results": results},
    })
    get_asset_storage().write_json(key(tenant_id, product_id), value)
    return value
