from __future__ import annotations

from io import BytesIO

from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.product_registration import (
    ApplySuggestionsBody,
    NewProductBody,
    apply_suggestions,
    get_registration,
    register_product,
    suggest_product_info,
)
from app.db.models import Base, BusinessWorkspace, ImageReferenceAsset
from app.db.product_image_fact import ProductImageFact
from app.db.product_registration import ProductRegistrationProfile
from app.services import image_studio, product_image_fact
from app.services.product_image_fact import confirm_image_fact, create_upload_row
from app.services.product_image_final_policy_patch import install_product_image_final_policy_patch


TENANT = "__smoke__"


def _db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    # These models live in separate modules but share Base.metadata after import.
    ProductRegistrationProfile.__table__.create(engine, checkfirst=True)
    ProductImageFact.__table__.create(engine, checkfirst=True)
    return Session(engine)


def _png(width: int = 400, height: int = 300) -> bytes:
    image = Image.new("RGBA", (width, height), (120, 140, 160, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _transparent_cutout(_: bytes) -> bytes:
    image = Image.new("RGBA", (400, 300), (0, 0, 0, 0))
    for x in range(80, 320):
        for y in range(60, 240):
            image.putpixel((x, y), (40, 80, 120, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_product_registration_full_flow_reaches_reusable_product_master(tmp_path, monkeypatch):
    db = _db()
    try:
        workspace = BusinessWorkspace(
            tenant_id=TENANT,
            name="Smoke Workspace",
            slug="smoke-workspace",
            business_type="commerce",
            mode="shadow",
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)

        registered = register_product(
            NewProductBody(
                workspace_id=workspace.id,
                product_code="SMOKE-PRODUCT-001",
                name="스모크 테스트 상품",
                model_name="SM-001",
                primary_material="steel",
                country_of_origin="KR",
                dimensions={"length": "100 mm", "width": "80 mm", "height": "60 mm"},
                packaging={"individual": "1 pc", "box": "10 pcs"},
                confirm=True,
                confirmed_by="smoke-test",
            ),
            tenant_id=TENANT,
            db=db,
        )
        product_id = registered["product"]["id"]
        assert registered["facts"]["confirmed"] is True

        # Product image path: temporary capture -> cutout -> standard Fit -> final-only asset.
        # Storage and resolver must share the same isolated root, just like production.
        monkeypatch.setattr(product_image_fact, "media_root", lambda: tmp_path)
        monkeypatch.setattr(image_studio, "media_root", lambda: tmp_path)
        install_product_image_final_policy_patch()
        monkeypatch.setattr(product_image_fact, "remove_background", _transparent_cutout)

        image_row = create_upload_row(
            db,
            tenant_id=TENANT,
            product_id=product_id,
            filename="product.png",
            mime_type="image/png",
            content=_png(),
            slot_hint="RIGHT_45",
            auto_process=True,
        )
        db.commit()
        db.refresh(image_row)
        assert image_row.fact_asset_uri

        confirm_image_fact(db, row=image_row, confirmed_by="smoke-test")
        db.commit()
        db.refresh(image_row)
        assert image_row.status == "confirmed"
        assert image_row.raw_asset_uri is None
        assert image_row.reference_asset_id

        reference = db.get(ImageReferenceAsset, image_row.reference_asset_id)
        assert reference is not None
        assert reference.asset_uri == image_row.fact_asset_uri

        final_path = product_image_fact.resolve_media_uri(image_row.fact_asset_uri)
        with Image.open(final_path) as final_image:
            assert final_image.size == (1000, 1000)
            assert final_image.mode == "RGB"

        suggestion_result = suggest_product_info(product_id, tenant_id=TENANT, db=db)
        assert suggestion_result["fact_mutation_allowed"] is False
        assert suggestion_result["suggestions"]["marketing"]["features"]

        apply_suggestions(
            product_id,
            ApplySuggestionsBody(
                operating_info=suggestion_result["suggestions"].get("operating") or {},
                marketing_info=suggestion_result["suggestions"].get("marketing") or {},
            ),
            tenant_id=TENANT,
            db=db,
        )

        master = get_registration(product_id, tenant_id=TENANT, db=db)
        assert master["facts"]["model_name"] == "SM-001"
        assert master["facts"]["primary_material"] == "steel"
        assert master["facts"]["country_of_origin"] == "KR"
        assert master["images"]["primary_asset_id"] == reference.id
        assert master["marketing_info"]["features"]
    finally:
        db.close()
