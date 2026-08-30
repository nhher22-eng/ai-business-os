from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import BusinessWorkspace, DetailPageTemplate
from app.db.session import SessionLocal


router = APIRouter(
    prefix="/api/v1/detail-page-template-settings",
    tags=["detail-page-template-settings"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SECTION_CATALOG = [
    {"type": "HERO", "name": "메인·핵심 소개", "default_required": True, "data": ["상품명", "핵심문구", "HERO 이미지"]},
    {"type": "PROBLEM", "name": "구매 필요성·사용 목적", "default_required": False, "data": ["사용 용도", "사용 상황"]},
    {"type": "LIFESTYLE", "name": "실제 사용 모습", "default_required": False, "data": ["사용 정보", "LIFESTYLE 이미지"]},
    {"type": "FEATURE", "name": "제품 핵심 특징", "default_required": True, "data": ["확정 특징", "재질", "상품 FACT"]},
    {"type": "OPTION_COMPARE", "name": "옵션 비교", "default_required": False, "data": ["SKU", "옵션"]},
    {"type": "COMPONENTS", "name": "구성품", "default_required": False, "data": ["확정 구성품"]},
    {"type": "INSTALLATION", "name": "사용·설치방법", "default_required": False, "data": ["사용방법", "설치방법"]},
    {"type": "SPEC", "name": "제품 상세정보·규격", "default_required": True, "data": ["치수 FACT", "제품 사양", "SPEC 이미지"]},
    {"type": "CAUTION", "name": "주의사항", "default_required": False, "data": ["주의사항", "사용 조건"]},
    {"type": "FAQ", "name": "자주 묻는 질문", "default_required": False, "data": ["FACT 기반 예상 질문", "사용법", "주의사항"]},
    {"type": "ADD_ON", "name": "추가상품", "default_required": False, "data": ["추가상품 관계"]},
    {"type": "RELATED_PRODUCTS", "name": "관련상품", "default_required": False, "data": ["관련상품 관계"]},
]


DEFAULT_CONTENT_RULES = {
    "sections": [
        {"type": "HERO", "name": "메인·핵심 소개", "enabled": True, "required": True, "condition": "always", "sort_order": 10},
        {"type": "FEATURE", "name": "제품 핵심 특징", "enabled": True, "required": True, "condition": "always", "sort_order": 20},
        {"type": "LIFESTYLE", "name": "실제 사용 모습", "enabled": True, "required": False, "condition": "approved_lifestyle_image_exists", "sort_order": 30},
        {"type": "SPEC", "name": "제품 상세정보·규격", "enabled": True, "required": True, "condition": "confirmed_fact_exists", "sort_order": 40},
        {"type": "INSTALLATION", "name": "사용·설치방법", "enabled": True, "required": False, "condition": "installation_or_usage_exists", "sort_order": 50},
        {"type": "CAUTION", "name": "주의사항", "enabled": True, "required": False, "condition": "caution_exists", "sort_order": 60},
        {"type": "FAQ", "name": "자주 묻는 질문", "enabled": True, "required": False, "condition": "faq_fact_source_exists", "sort_order": 70},
    ],
    "review_policy": "exclude_without_verified_source",
    "faq_policy": "fact_based_guidance_only",
    "allow_product_override": True,
}


DEFAULT_FIELD_BINDINGS = {
    "hero.title": "product.name",
    "hero.subtitle": "content_basis.headline",
    "hero.image": "approved_image.HERO",
    "feature.items": "content_basis.features",
    "lifestyle.image": "approved_image.LIFESTYLE",
    "lifestyle.body": "product_detail.usage",
    "spec.dimensions": "registration_fact.dimensions",
    "spec.material": "registration_fact.primary_material",
    "installation.body": "product_detail.installation_method",
    "caution.body": "product_detail.cautions",
    "faq.items": "fact_based_faq.items",
}


class TemplateCreateBody(BaseModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=64)
    description: str | None = None
    canva_brand_template_id: str | None = None
    canva_design_id: str | None = None
    canva_edit_url: str | None = None
    content_rules: dict[str, Any] | None = None
    field_bindings: dict[str, Any] | None = None
    category_scope: dict[str, Any] | None = None
    channel_scope: dict[str, Any] | None = None
    layout_rules: dict[str, Any] | None = None


class TemplateUpdateBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    canva_brand_template_id: str | None = None
    canva_design_id: str | None = None
    canva_edit_url: str | None = None
    content_rules: dict[str, Any] | None = None
    field_bindings: dict[str, Any] | None = None
    category_scope: dict[str, Any] | None = None
    channel_scope: dict[str, Any] | None = None
    layout_rules: dict[str, Any] | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _code(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_").upper()
    return result[:52] or "DETAIL_TEMPLATE"


def _workspace(db: Session, tenant_id: str, workspace_id: str) -> BusinessWorkspace:
    row = db.scalar(
        select(BusinessWorkspace).where(
            BusinessWorkspace.id == workspace_id,
            BusinessWorkspace.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="workspace not found")
    return row


def _template(db: Session, tenant_id: str, template_id: str) -> DetailPageTemplate:
    row = db.scalar(
        select(DetailPageTemplate).where(
            DetailPageTemplate.id == template_id,
            DetailPageTemplate.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="template not found")
    return row


def _payload(row: DetailPageTemplate) -> dict[str, Any]:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "code": row.code,
        "name": row.name,
        "description": row.description,
        "version_no": row.version_no,
        "parent_template_id": row.parent_template_id,
        "status": row.status,
        "layout_rules": row.layout_rules or {},
        "content_rules": row.content_rules or {},
        "field_bindings": row.field_bindings or {},
        "category_scope": row.category_scope or {},
        "channel_scope": row.channel_scope or {},
        "canva_brand_template_id": row.canva_brand_template_id,
        "canva_design_id": row.canva_design_id,
        "canva_edit_url": row.canva_edit_url,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "locked": row.status in {"active", "retired"},
    }


def _validation(row: DetailPageTemplate) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    rules = row.content_rules or {}
    sections = rules.get("sections") if isinstance(rules, dict) else None
    bindings = row.field_bindings or {}

    if not row.name.strip():
        errors.append("템플릿 이름이 필요합니다.")
    if not isinstance(sections, list) or not sections:
        errors.append("사용할 상세페이지 섹션을 하나 이상 설정하세요.")
        sections = []

    enabled = [s for s in sections if isinstance(s, dict) and s.get("enabled", True)]
    if not enabled:
        errors.append("활성화된 섹션이 없습니다.")

    section_types = [str(s.get("type", "")).strip() for s in enabled]
    if len(section_types) != len(set(section_types)):
        errors.append("같은 섹션이 중복 등록되어 있습니다.")
    if "HERO" not in section_types:
        warnings.append("메인·핵심 소개(HERO) 섹션이 없습니다.")
    if "REVIEW_SUMMARY" in section_types or "REVIEW_DETAIL" in section_types:
        warnings.append("리뷰 섹션은 실제 검증 리뷰가 있을 때만 사용해야 합니다.")
    if "FAQ" not in section_types:
        warnings.append("사용법·주의사항 안내를 위한 FAQ 섹션이 없습니다.")

    required_bindings = []
    for section in enabled:
        if not isinstance(section, dict) or not section.get("required"):
            continue
        stype = str(section.get("type", "")).lower()
        required_bindings.extend(
            key for key in bindings if str(key).lower().startswith(stype + ".")
        )
        if not any(str(key).lower().startswith(stype + ".") for key in bindings):
            errors.append(f"필수 섹션 {section.get('type')}의 요소 연결이 없습니다.")

    if not (row.canva_design_id or row.canva_brand_template_id or row.canva_edit_url):
        errors.append("Canva 원본 디자인 또는 템플릿 연결정보가 필요합니다.")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "enabled_section_count": len(enabled),
        "binding_count": len(bindings),
    }


@router.get("/catalog")
def template_catalog():
    return {
        "sections": SECTION_CATALOG,
        "default_content_rules": DEFAULT_CONTENT_RULES,
        "default_field_bindings": DEFAULT_FIELD_BINDINGS,
        "statuses": ["draft", "testing", "active", "retired"],
    }


@router.get("")
def list_templates(
    tenant_id: str = Query(..., min_length=1, max_length=128),
    workspace_id: str = Query(...),
    include_retired: bool = Query(False),
    db: Session = Depends(get_db),
):
    _workspace(db, tenant_id, workspace_id)
    query = (
        select(DetailPageTemplate)
        .where(
            DetailPageTemplate.tenant_id == tenant_id,
            or_(
                DetailPageTemplate.workspace_id == workspace_id,
                DetailPageTemplate.workspace_id.is_(None),
            ),
        )
        .order_by(DetailPageTemplate.name, DetailPageTemplate.version_no.desc())
    )
    rows = db.scalars(query).all()
    if not include_retired:
        rows = [row for row in rows if row.status != "retired"]
    return [_payload(row) for row in rows]


@router.get("/{template_id}")
def get_template(
    template_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    return _payload(_template(db, tenant_id, template_id))


@router.post("")
def create_template(
    body: TemplateCreateBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _workspace(db, tenant_id, body.workspace_id)
    base_code = _code(body.code or body.name)
    code = base_code
    suffix = 1
    while db.scalar(
        select(DetailPageTemplate.id).where(
            DetailPageTemplate.tenant_id == tenant_id,
            DetailPageTemplate.code == code,
        )
    ):
        suffix += 1
        code = f"{base_code[:52]}_{suffix}"

    row = DetailPageTemplate(
        tenant_id=tenant_id,
        workspace_id=body.workspace_id,
        code=code,
        name=body.name.strip(),
        description=body.description,
        version_no=1,
        content_rules=body.content_rules or DEFAULT_CONTENT_RULES,
        field_bindings=body.field_bindings or DEFAULT_FIELD_BINDINGS,
        category_scope=body.category_scope or {"mode": "all", "values": []},
        channel_scope=body.channel_scope or {"mode": "selected", "values": ["naver-smartstore"]},
        layout_rules=body.layout_rules or {},
        canva_brand_template_id=body.canva_brand_template_id,
        canva_design_id=body.canva_design_id,
        canva_edit_url=body.canva_edit_url,
        status="draft",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _payload(row)


@router.put("/{template_id}")
def update_template(
    template_id: str,
    body: TemplateUpdateBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = _template(db, tenant_id, template_id)
    if row.status in {"active", "retired"}:
        raise HTTPException(
            409,
            detail="확정 또는 사용 중지된 템플릿은 직접 수정할 수 없습니다. 새 버전을 만드세요.",
        )
    values = body.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(row, key, value)
    row.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return _payload(row)


@router.post("/{template_id}/new-version")
def new_template_version(
    template_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    source = _template(db, tenant_id, template_id)
    version_no = int(source.version_no or 1) + 1
    base_code = re.sub(r"_V\d+$", "", source.code)
    code = f"{base_code[:54]}_V{version_no}"
    while db.scalar(
        select(DetailPageTemplate.id).where(
            DetailPageTemplate.tenant_id == tenant_id,
            DetailPageTemplate.code == code,
        )
    ):
        version_no += 1
        code = f"{base_code[:54]}_V{version_no}"

    row = DetailPageTemplate(
        tenant_id=source.tenant_id,
        workspace_id=source.workspace_id,
        code=code,
        name=source.name,
        description=source.description,
        version_no=version_no,
        parent_template_id=source.id,
        content_rules=source.content_rules or DEFAULT_CONTENT_RULES,
        field_bindings=source.field_bindings or DEFAULT_FIELD_BINDINGS,
        category_scope=source.category_scope or {"mode": "all", "values": []},
        channel_scope=source.channel_scope or {"mode": "selected", "values": ["naver-smartstore"]},
        layout_rules=source.layout_rules,
        canva_brand_template_id=source.canva_brand_template_id,
        canva_design_id=source.canva_design_id,
        canva_edit_url=source.canva_edit_url,
        status="draft",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _payload(row)


@router.post("/{template_id}/validate")
def validate_template(
    template_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = _template(db, tenant_id, template_id)
    result = _validation(row)
    if row.status == "draft":
        row.status = "testing"
        row.updated_at = _utcnow()
        db.commit()
    return result


@router.post("/{template_id}/publish")
def publish_template(
    template_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = _template(db, tenant_id, template_id)
    if row.status == "retired":
        raise HTTPException(409, detail="사용 중지된 템플릿은 확정할 수 없습니다. 새 버전을 만드세요.")
    result = _validation(row)
    if not result["valid"]:
        raise HTTPException(409, detail={"message": "템플릿 검증을 통과하지 못했습니다.", **result})

    if row.parent_template_id:
        parent = db.scalar(
            select(DetailPageTemplate).where(
                DetailPageTemplate.id == row.parent_template_id,
                DetailPageTemplate.tenant_id == tenant_id,
            )
        )
        if parent and parent.status == "active":
            parent.status = "retired"
            parent.updated_at = _utcnow()

    row.status = "active"
    row.published_at = _utcnow()
    row.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return _payload(row)


@router.post("/{template_id}/retire")
def retire_template(
    template_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = _template(db, tenant_id, template_id)
    if row.status != "active":
        raise HTTPException(409, detail="사용 중인 확정 템플릿만 사용 중지할 수 있습니다.")
    row.status = "retired"
    row.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return _payload(row)
