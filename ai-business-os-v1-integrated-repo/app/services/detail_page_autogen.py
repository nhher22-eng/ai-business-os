from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    BrandStyleSheet,
    BusinessWorkspace,
    DetailPageJob,
    DetailPageQAResult,
    DetailPageTemplate,
    DetailPageVersion,
    Product,
    ProductRelation,
    ReviewSource,
)
from app.services.detail_page_studio import (
    create_prepared_version,
    ensure_defaults,
    product_snapshot,
    qa_summary,
    run_qa,
    version_sections,
)


CONDITIONAL_SECTION_RULES = {
    "REVIEW_SUMMARY": "reviews",
    "REVIEW_DETAIL": "reviews",
    "ADD_ON": "add_on",
    "RELATED_PRODUCTS": "related_products",
}


@dataclass(frozen=True)
class AutoGenerateResult:
    job: DetailPageJob
    version: DetailPageVersion
    qa_rows: list[DetailPageQAResult]
    enabled_sections: list[str]
    hidden_sections: list[str]
    qa_summary: str

    @property
    def release_ready(self) -> bool:
        return self.qa_summary == "PASS"


def fact_readiness(snapshot: dict) -> dict:
    """Evaluate whether Product DB facts are sufficient for a selling-page release.

    The rule is intentionally conservative. A product name alone is enough to
    prepare a draft, but not enough to approve/export a selling page. At least
    one meaningful ProductDetail fact or one SKU must exist. Missing values are
    never inferred from memory, copy, or images.
    """
    product = snapshot.get("product") or {}
    detail = snapshot.get("detail") or {}
    skus = snapshot.get("skus") or []

    detail_values = [
        detail.get("specification"),
        detail.get("usage"),
        detail.get("installation_method"),
        detail.get("usage_conditions"),
        detail.get("cautions"),
    ]
    has_detail_fact = any(bool(str(value).strip()) for value in detail_values if value is not None)
    has_sku_fact = bool(skus)
    has_name = bool(str(product.get("name") or "").strip())

    missing = []
    if not has_name:
        missing.append("product.name")
    if not has_detail_fact and not has_sku_fact:
        missing.append("product_detail_or_sku")

    return {
        "ready": not missing,
        "missing": missing,
        "has_product_name": has_name,
        "has_detail_fact": has_detail_fact,
        "has_sku_fact": has_sku_fact,
    }


def _has_verified_reviews(db: Session, *, tenant_id: str, product_id: str) -> bool:
    return db.scalar(
        select(ReviewSource.id).where(
            ReviewSource.tenant_id == tenant_id,
            ReviewSource.product_id == product_id,
            ReviewSource.is_verified.is_(True),
        ).limit(1)
    ) is not None


def _has_relation(
    db: Session,
    *,
    tenant_id: str,
    product_id: str,
    relation_type: str,
) -> bool:
    return db.scalar(
        select(ProductRelation.id).where(
            ProductRelation.tenant_id == tenant_id,
            ProductRelation.source_product_id == product_id,
            ProductRelation.relation_type == relation_type,
            ProductRelation.is_active.is_(True),
        ).limit(1)
    ) is not None


def _conditional_availability(db: Session, *, tenant_id: str, product_id: str) -> dict[str, bool]:
    return {
        "reviews": _has_verified_reviews(db, tenant_id=tenant_id, product_id=product_id),
        "add_on": _has_relation(
            db,
            tenant_id=tenant_id,
            product_id=product_id,
            relation_type="ADD_ON",
        ),
        "related_products": _has_relation(
            db,
            tenant_id=tenant_id,
            product_id=product_id,
            relation_type="RELATED_PRODUCT",
        ),
    }


def apply_release_candidate_rules(
    db: Session,
    *,
    job: DetailPageJob,
    version: DetailPageVersion,
) -> tuple[list[str], list[str]]:
    """Apply deterministic page-inclusion rules without inventing missing data."""
    availability = _conditional_availability(
        db,
        tenant_id=job.tenant_id,
        product_id=job.product_id,
    )
    enabled: list[str] = []
    hidden: list[str] = []

    for section in version_sections(db, version.id):
        source_key = CONDITIONAL_SECTION_RULES.get(section.section_type)
        if source_key is not None and not availability[source_key]:
            section.is_enabled = False
            section.is_required = False
            section.qa_status = "hidden"
            hidden.append(section.section_type)
            continue

        if section.is_enabled:
            enabled.append(section.section_type)
        else:
            hidden.append(section.section_type)

    version.status = "release_candidate_review"
    job.status = "release_candidate_review"
    db.flush()
    return enabled, hidden


def _reconcile_conditional_required_sections(
    db: Session,
    *,
    version: DetailPageVersion,
    qa_rows: list[DetailPageQAResult],
) -> None:
    sections = version_sections(db, version.id)
    enabled_types = {s.section_type for s in sections if s.is_enabled}
    effective_required = {s.section_type for s in sections if s.is_required}
    missing = sorted(effective_required - enabled_types)

    row = next((q for q in qa_rows if q.check_code == "REQUIRED_SECTIONS"), None)
    if row is None:
        return
    if missing:
        row.status = "FAIL"
        row.severity = "error"
        row.message = f"필수 섹션 누락: {', '.join(missing)}"
        row.suggested_fix = "필수 섹션을 다시 활성화하세요."
    else:
        row.status = "PASS"
        row.severity = "info"
        row.message = "조건부 페이지 규칙을 반영한 필수 상세페이지 섹션이 모두 존재합니다."
        row.suggested_fix = None
    db.flush()


def _apply_fact_readiness_gate(
    db: Session,
    *,
    job: DetailPageJob,
    version: DetailPageVersion,
    qa_rows: list[DetailPageQAResult],
) -> dict:
    readiness = fact_readiness(
        product_snapshot(db, tenant_id=job.tenant_id, product_id=job.product_id)
    )
    if readiness["ready"]:
        row = DetailPageQAResult(
            tenant_id=job.tenant_id,
            job_id=job.id,
            version_no=version.version_no,
            check_code="FACT_READINESS",
            status="PASS",
            severity="info",
            message="판매용 상세페이지 생성에 필요한 최소 상품 FACT가 등록되어 있습니다.",
            resolved=False,
        )
    else:
        row = DetailPageQAResult(
            tenant_id=job.tenant_id,
            job_id=job.id,
            version_no=version.version_no,
            check_code="FACT_READINESS",
            status="FAIL",
            severity="error",
            message="판매용 상세페이지를 승인하기 위한 확정 상품 FACT가 부족합니다. 미확정 값은 추정하지 않습니다.",
            suggested_fix="ProductDetail의 확정 사양/사용정보를 등록하거나 실제 SKU를 등록한 뒤 다시 생성하세요.",
            resolved=False,
        )
    db.add(row)
    qa_rows.append(row)
    db.flush()
    return readiness


def auto_generate_release_candidate(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    product_id: str,
    channel: str = "naver-smartstore",
    page_length: str = "long",
    template_code: str = "A_PRACTICAL_TRUST",
    visual_style: str = "natural",
    page_strategy: str = "standard",
    brand_style_sheet_id: str | None = None,
    created_by: str | None = None,
) -> AutoGenerateResult:
    workspace = db.scalar(
        select(BusinessWorkspace).where(
            BusinessWorkspace.id == workspace_id,
            BusinessWorkspace.tenant_id == tenant_id,
        )
    )
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
        )
    )
    if workspace is None or product is None or product.workspace_id != workspace.id:
        raise ValueError("workspace/product not found")

    default_brand, templates = ensure_defaults(
        db,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
    )
    template = next((item for item in templates if item.code == template_code), None)
    if template is None:
        template = db.scalar(
            select(DetailPageTemplate).where(
                DetailPageTemplate.tenant_id == tenant_id,
                DetailPageTemplate.code == template_code,
            )
        )
    if template is None:
        raise ValueError("template not found")

    brand = default_brand
    if brand_style_sheet_id:
        brand = db.scalar(
            select(BrandStyleSheet).where(
                BrandStyleSheet.id == brand_style_sheet_id,
                BrandStyleSheet.tenant_id == tenant_id,
                BrandStyleSheet.workspace_id == workspace_id,
            )
        )
        if brand is None:
            raise ValueError("brand style not found")

    job = DetailPageJob(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        product_id=product_id,
        channel=channel,
        page_length=page_length,
        created_by=created_by,
        status="generating",
    )
    db.add(job)
    db.flush()

    version = create_prepared_version(
        db,
        job=job,
        template=template,
        brand=brand,
        visual_style=visual_style,
        page_strategy=page_strategy,
        change_summary="M06 자동생성 v1 · FACT/승인이미지 기반 Release Candidate 생성",
    )
    enabled, hidden = apply_release_candidate_rules(db, job=job, version=version)

    qa_rows = run_qa(db, job=job, version=version)
    _reconcile_conditional_required_sections(db, version=version, qa_rows=qa_rows)
    _apply_fact_readiness_gate(db, job=job, version=version, qa_rows=qa_rows)
    summary = qa_summary(qa_rows)
    job.status = "release_candidate_review"
    version.status = "release_candidate_review"
    db.flush()

    return AutoGenerateResult(
        job=job,
        version=version,
        qa_rows=qa_rows,
        enabled_sections=enabled,
        hidden_sections=hidden,
        qa_summary=summary,
    )
