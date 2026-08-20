from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.product_registration_readiness import registration_readiness
from app.db.models import Base, BusinessWorkspace, Product
from app.db.product_image_fact import ProductImageFact
from app.db.product_registration import ProductRegistrationProfile
from app.product_image_fact_ui_patch import inject_product_image_fact_ui
from app.product_registration_async_restore_ui_patch import inject_async_restore_ui
from app.product_registration_readiness_ui_patch import inject_product_registration_readiness_ui
from app.product_registration_ui import HTML


TENANT = "__readiness__"


def _db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    ProductRegistrationProfile.__table__.create(engine, checkfirst=True)
    ProductImageFact.__table__.create(engine, checkfirst=True)
    return Session(engine)


def _setup(db: Session):
    workspace = BusinessWorkspace(
        tenant_id=TENANT,
        name="Readiness Workspace",
        slug="readiness-workspace",
        business_type="commerce",
        mode="shadow",
    )
    db.add(workspace)
    db.flush()
    product = Product(
        tenant_id=TENANT,
        workspace_id=workspace.id,
        product_code="READY-001",
        name="Readiness Product",
        status="draft",
    )
    db.add(product)
    db.flush()
    profile = ProductRegistrationProfile(
        tenant_id=TENANT,
        product_id=product.id,
        facts_confirmed=False,
        additional_image_asset_ids=[],
    )
    db.add(profile)
    db.commit()
    return product, profile


def _confirmed_image(product_id: str, slot_type: str, index: int = 1):
    return ProductImageFact(
        tenant_id=TENANT,
        product_id=product_id,
        slot_type=slot_type,
        slot_index=index,
        is_required=slot_type in {"RIGHT_45", "FRONT"},
        is_primary=slot_type == "RIGHT_45",
        status="confirmed",
        source_kind="temporary_capture",
        fact_asset_uri=f"media://facts/{slot_type.lower()}.png",
        original_filename=f"{slot_type.lower()}.png",
        mime_type="image/png",
        classification_source="user",
        background_removed=True,
        keep_background=False,
        raw_retention_policy="final_only",
    )


def test_registration_readiness_blocks_until_fact_and_required_images_are_confirmed():
    db = _db()
    try:
        product, profile = _setup(db)

        initial = registration_readiness(db, tenant_id=TENANT, product_id=product.id)
        assert initial["ready"] is False
        assert "기본 FACT 사용자 확정" in initial["missing_labels"]
        assert "45도 우측" in initial["missing_labels"]
        assert "정면" in initial["missing_labels"]

        profile.facts_confirmed = True
        profile.primary_image_asset_id = "primary-reference"
        db.add(_confirmed_image(product.id, "RIGHT_45"))
        db.commit()

        one_missing = registration_readiness(db, tenant_id=TENANT, product_id=product.id)
        assert one_missing["ready"] is False
        assert one_missing["facts_confirmed"] is True
        assert one_missing["primary_asset_linked"] is True
        assert one_missing["missing_image_slots"] == ["FRONT"]

        db.add(_confirmed_image(product.id, "FRONT"))
        db.commit()

        complete = registration_readiness(db, tenant_id=TENANT, product_id=product.id)
        assert complete["ready"] is True
        assert complete["missing_labels"] == []
        assert complete["images_ready"] is True
        assert complete["product_status"] == "draft"
        assert "핵심 등록 완료" in complete["note"]
    finally:
        db.close()


def test_registration_ui_uses_final_only_policy_copy_and_backend_readiness():
    html = inject_product_image_fact_ui(HTML)
    html = inject_async_restore_ui(html)
    html = inject_product_registration_readiness_ui(html)

    assert "누끼 + 1000×1000 표준 Fit" in html
    assert "부분상세/라이프스타일: 최종 사용본 1개만" in html
    assert "각도/상세사진: 촬영 원본은 임시" not in html
    assert "라이프스타일: 촬영 원본 자체를 FACT로 보관" not in html
    assert "/readiness?tenant_id=${tenant}" in html
    assert "Product Master 완료 전 보완" in html
    assert "await checkRegistrationReadiness();" in html
