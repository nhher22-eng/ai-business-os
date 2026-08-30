from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.content_copy import ContentCopyAsset
from app.db.models import Product
from app.db.product_registration import ProductRegistrationProfile
from app.db.session import SessionLocal
from app.services.canva_v12_text_export import CANVA_V12_COPY_FIELDS
from app.services.canva_v12_copy_ai import generate_canva_v12_copy_candidates


router = APIRouter(
    prefix="/api/v1/content-copy",
    tags=["content-copy"],
    dependencies=[Depends(require_business_auth)],
)


TARGET_SLOTS = {
    "detail_page": [
        ("headline", "메인 헤드라인"),
        ("subheadline", "보조 헤드라인"),
        ("feature_summary", "핵심 특징"),
        ("usage", "사용 용도"),
        ("specification", "규격 설명"),
        ("caution", "구매 전 확인"),
    ],
    "catalog": [
        ("product_name", "상품명"),
        ("short_description", "한 줄 소개"),
        ("feature_summary", "핵심 특징"),
        ("specification", "주요 규격"),
    ],
    "advertisement": [
        ("headline", "광고 헤드라인"),
        ("benefit", "고객 효익"),
        ("cta", "행동 유도 문구"),
    ],
    "manual": [
        ("purpose", "제품 용도"),
        ("installation", "설치 방법"),
        ("usage", "사용 방법"),
        ("caution", "주의사항"),
    ],
    "canva_v12": [
        (field_name, field_name) for field_name in CANVA_V12_COPY_FIELDS
    ],
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def utcnow():
    return datetime.now(timezone.utc)


def _product_and_profile(db: Session, tenant_id: str, product_id: str):
    product = db.scalar(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    if product is None:
        raise HTTPException(404, detail="product not found")
    profile = db.scalar(
        select(ProductRegistrationProfile).where(
            ProductRegistrationProfile.product_id == product_id,
            ProductRegistrationProfile.tenant_id == tenant_id,
        )
    )
    return product, profile


def _facts(product: Product, profile: ProductRegistrationProfile | None) -> dict:
    operating = (profile.operating_info or {}) if profile else {}
    marketing = (profile.marketing_info or {}) if profile else {}
    return {
        "product_name": product.name,
        "description": product.description or "",
        "model_name": profile.model_name if profile else None,
        "material": profile.primary_material if profile else None,
        "weight": profile.weight if profile else None,
        "dimensions": profile.dimensions or {} if profile else {},
        "usage": operating.get("usage") or marketing.get("usage"),
        "installation": operating.get("installation_method"),
        "features": marketing.get("features") or marketing.get("selling_points"),
        "caution": operating.get("cautions") or (profile.fact_notes if profile else None),
        "facts_confirmed": bool(profile and profile.facts_confirmed),
    }


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    if isinstance(value, dict):
        return " · ".join(f"{k} {v}" for k, v in value.items() if v)
    return str(value).strip()


def _candidate(slot_key: str, facts: dict) -> tuple[str, list[str], str]:
    name = _text(facts["product_name"])
    features = _text(facts["features"])
    usage = _text(facts["usage"])
    dimensions = _text(facts["dimensions"])
    material = _text(facts["material"])
    mapping = {
        "product_name": (name, ["product.name"], "fact_substitution"),
        "headline": (features or name, ["marketing_info.features"] if features else ["product.name"], "fact_substitution"),
        "subheadline": (usage or _text(facts["description"]), ["operating_info.usage"] if usage else ["product.description"], "fact_substitution"),
        "short_description": (_text(facts["description"]) or usage or name, ["product.description"], "fact_substitution"),
        "feature_summary": (features, ["marketing_info.features"], "fact_substitution"),
        # No model is called in this endpoint. Even customer-facing benefit
        # text remains a direct FACT substitution until a real AI provider is
        # explicitly invoked and recorded.
        "benefit": (features, ["marketing_info.features"], "fact_substitution"),
        "usage": (usage, ["operating_info.usage"], "fact_substitution"),
        "purpose": (usage, ["operating_info.usage"], "fact_substitution"),
        "specification": (" · ".join(v for v in (dimensions, material) if v), ["dimensions", "primary_material"], "fact_substitution"),
        "installation": (_text(facts["installation"]), ["operating_info.installation_method"], "fact_substitution"),
        "caution": (_text(facts["caution"]), ["operating_info.cautions", "fact_notes"], "fact_substitution"),
        "cta": ("상품 정보를 확인해 보세요.", [], "system_default"),
        "hero_headline": (features or name, ["marketing_info.features"] if features else ["product.name"], "fact_substitution"),
        "hero_subcopy": (usage or _text(facts["description"]), ["operating_info.usage"] if usage else ["product.description"], "fact_substitution"),
        "features_section_subcopy": (features, ["marketing_info.features"], "fact_substitution"),
        "usage_scene_section_subcopy": (usage, ["operating_info.usage"], "fact_substitution"),
        "spec_section_subcopy": (" · ".join(v for v in (dimensions, material) if v), ["dimensions", "primary_material"], "fact_substitution"),
        "caution_section_subcopy": (_text(facts["caution"]), ["operating_info.cautions", "fact_notes"], "fact_substitution"),
    }
    return mapping.get(slot_key, ("", [], "fact_substitution"))


class SaveCandidateBody(BaseModel):
    target_type: Literal["detail_page", "catalog", "advertisement", "manual", "canva_v12"]
    slot_key: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=5000)
    source_fact_keys: list[str] = []
    generation_method: Literal["fact_substitution", "ai_assisted", "system_default", "user_written"] = "user_written"


class ApprovalBody(BaseModel):
    approved: bool = True
    approved_by: str = Field(default="dashboard-user", min_length=1, max_length=128)


class CanvaV12AIProposalBody(BaseModel):
    execution_approved: bool = False


@router.get("/requirements")
def requirements(target_type: str = Query(...)):
    slots = TARGET_SLOTS.get(target_type)
    if slots is None:
        raise HTTPException(422, detail="unsupported target type")
    return [{"slot_key": key, "slot_label": label} for key, label in slots]


@router.get("/products/{product_id}/candidates")
def candidates(
    product_id: str,
    target_type: str = Query(...),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    slots = TARGET_SLOTS.get(target_type)
    if slots is None:
        raise HTTPException(422, detail="unsupported target type")
    product, profile = _product_and_profile(db, tenant_id, product_id)
    facts = _facts(product, profile)
    return {
        "facts_confirmed": facts["facts_confirmed"],
        "slots": [
            {
                "slot_key": key,
                "slot_label": label,
                "content": _candidate(key, facts)[0],
                "source_fact_keys": _candidate(key, facts)[1],
                "generation_method": _candidate(key, facts)[2],
                "has_basis": bool(_candidate(key, facts)[0]),
            }
            for key, label in slots
        ],
    }


@router.post("/products/{product_id}/canva-v12/ai-candidates")
def canva_v12_ai_candidates(
    product_id: str,
    body: CanvaV12AIProposalBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    if not body.execution_approved:
        raise HTTPException(409, detail="AI 문안 후보 생성 실행 승인이 필요합니다.")
    product, profile = _product_and_profile(db, tenant_id, product_id)
    facts = _facts(product, profile)
    approved_rows = list(
        db.scalars(
            select(ContentCopyAsset).where(
                ContentCopyAsset.product_id == product_id,
                ContentCopyAsset.tenant_id == tenant_id,
                ContentCopyAsset.status == "approved",
            ).order_by(ContentCopyAsset.updated_at.desc())
        ).all()
    )
    approved: dict[str, str] = {}
    for row in approved_rows:
        approved.setdefault(row.slot_key, row.content)
    proposals, meta = generate_canva_v12_copy_candidates(
        product_name=product.name,
        confirmed_facts=facts,
        approved_copy=approved,
    )
    return {
        "proposals": proposals,
        "proposal_count": len(proposals),
        "requires_human_review": True,
        "saved": False,
        "approved": False,
        "meta": meta,
    }


@router.post("/products/{product_id}/assets")
def save_candidate(
    product_id: str,
    body: SaveCandidateBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    product, _ = _product_and_profile(db, tenant_id, product_id)
    labels = dict(TARGET_SLOTS[body.target_type])
    if body.slot_key not in labels:
        raise HTTPException(422, detail="slot does not belong to target type")
    latest = db.scalar(
        select(func.max(ContentCopyAsset.version_no)).where(
            ContentCopyAsset.tenant_id == tenant_id,
            ContentCopyAsset.product_id == product_id,
            ContentCopyAsset.target_type == body.target_type,
            ContentCopyAsset.slot_key == body.slot_key,
        )
    ) or 0
    row = ContentCopyAsset(
        tenant_id=tenant_id,
        workspace_id=product.workspace_id,
        product_id=product_id,
        target_type=body.target_type,
        slot_key=body.slot_key,
        slot_label=labels[body.slot_key],
        content=body.content.strip(),
        source_fact_keys=body.source_fact_keys,
        generation_method=body.generation_method,
        version_no=int(latest) + 1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _payload(row)


def _payload(row: ContentCopyAsset) -> dict:
    return {
        "id": row.id,
        "product_id": row.product_id,
        "target_type": row.target_type,
        "slot_key": row.slot_key,
        "slot_label": row.slot_label,
        "content": row.content,
        "status": row.status,
        "source_fact_keys": row.source_fact_keys or [],
        "generation_method": row.generation_method,
        "version_no": row.version_no,
        "approved_by": row.approved_by,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
    }


@router.post("/assets/{asset_id}/approval")
def approve_asset(
    asset_id: str,
    body: ApprovalBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(ContentCopyAsset).where(
            ContentCopyAsset.id == asset_id, ContentCopyAsset.tenant_id == tenant_id
        )
    )
    if row is None:
        raise HTTPException(404, detail="content copy asset not found")
    row.status = "approved" if body.approved else "rejected"
    row.approved_by = body.approved_by if body.approved else None
    row.approved_at = utcnow() if body.approved else None
    db.commit()
    db.refresh(row)
    return _payload(row)


@router.get("/products/{product_id}/assets")
def list_assets(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(ContentCopyAsset).where(
        ContentCopyAsset.product_id == product_id,
        ContentCopyAsset.tenant_id == tenant_id,
    )
    if status:
        stmt = stmt.where(ContentCopyAsset.status == status)
    rows = db.scalars(stmt.order_by(ContentCopyAsset.created_at.desc())).all()
    return [_payload(row) for row in rows]
