from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.product_overview import _master_readiness
from app.db.models import Base, BusinessWorkspace, Product
from app.db.product_image_fact import ProductImageFact
from app.db.product_registration import ProductRegistrationProfile
from app.product_overview_ui import HTML


TENANT = "__overview__"


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
        name="Overview Workspace",
        slug="overview-workspace",
        business_type="commerce",
        mode="shadow",
    )
    db.add(workspace)
    db.flush()
    product = Product(
        tenant_id=TENANT,
        workspace_id=workspace.id,
        product_code="OVERVIEW-001",
        name="Overview Product",
        status="draft",
    )
    db.add(product)
    db.flush()
    profile = ProductRegistrationProfile(
        tenant_id=TENANT,
        product_id=product.id,
        facts_confirmed=True,
        primary_image_asset_id="primary-reference",
        additional_image_asset_ids=[],
    )
    db.add(profile)
    db.commit()
    return product, profile


def _confirmed(product_id: str, slot: str):
    return ProductImageFact(
        tenant_id=TENANT,
        product_id=product_id,
        slot_type=slot,
        slot_index=1,
        is_required=True,
        is_primary=slot == "RIGHT_45",
        status="confirmed",
        source_kind="temporary_capture",
        fact_asset_uri=f"media://facts/{slot.lower()}.png",
        original_filename=f"{slot.lower()}.png",
        mime_type="image/png",
        classification_source="user",
        background_removed=True,
        keep_background=False,
        raw_retention_policy="final_only",
    )


def test_overview_readiness_exposes_missing_required_image_then_complete():
    db = _db()
    try:
        product, profile = _setup(db)
        db.add(_confirmed(product.id, "RIGHT_45"))
        db.commit()

        incomplete = _master_readiness(
            db,
            tenant_id=TENANT,
            product_id=product.id,
            profile=profile,
        )
        assert incomplete["ready"] is True
        assert incomplete["facts_confirmed"] is True
        assert incomplete["has_primary_image"] is True
        assert incomplete["missing_image_slots"] == ["FRONT"]
        assert incomplete["missing_labels"] == []

        db.add(_confirmed(product.id, "FRONT"))
        db.commit()
        complete = _master_readiness(
            db,
            tenant_id=TENANT,
            product_id=product.id,
            profile=profile,
        )
        assert complete["ready"] is True
        assert complete["missing_labels"] == []
        assert complete["images_ready"] is True
    finally:
        db.close()


def test_product_overview_ui_shows_master_completion_and_filter():
    assert 'id="masterCount"' in HTML
    assert 'id="needsCount"' in HTML
    assert 'id="masterFilter"' in HTML
    assert 'value="ready">등록 완료' in HTML
    assert 'value="needs">보완 필요' in HTML
    assert '<th>Product Master</th>' in HTML
    assert "x.master_ready" in HTML
    assert "x.master_missing_labels" in HTML
    assert "선택 · 미작성" in HTML
