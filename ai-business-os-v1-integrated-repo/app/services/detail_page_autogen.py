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
    """Make REQUIRED_SECTIONS QA honor per-version conditional required flags.

    The legacy M06 QA uses a global required-section set. Auto-generation can
    intentionally hide review/add-on/related sections when their source data is
    absent. In that case those sections are marked is_required=False, so the
    release-candidate QA must evaluate the version's effective required set.
    """
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
    summary = qa_summary(qa_rows)
    # run_qa moves the job into qa_review; keep the more specific pipeline state.
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
