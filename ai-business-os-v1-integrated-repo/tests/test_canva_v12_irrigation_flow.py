from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import canva_controlled_export, content_copy
from app.api.dashboard_session import require_business_auth
from app.db.content_copy import ContentCopyAsset
from app.db.models import Base, BusinessWorkspace, Product, ProductSKU
from app.db.product_registration import ProductRegistrationProfile


TENANT = "canva-v12-irrigation-test"


def test_irrigation_ai_candidate_requires_approval_before_canva_draft(monkeypatch):
    app = FastAPI()
    app.include_router(content_copy.router)
    app.include_router(canva_controlled_export.router)
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        workspace = BusinessWorkspace(
            tenant_id=TENANT,
            name="Commerce AI Workspace",
            slug="commerce-ai",
            business_type="commerce",
            mode="shadow",
        )
        db.add(workspace)
        db.flush()
        product = Product(
            tenant_id=TENANT,
            workspace_id=workspace.id,
            product_code="IRRIGATION-8MM-KIT",
            name="8mm 자동 관수키트",
            description="8mm 마이크로 스프레이 자동 관수키트",
            manufacturer="확정 제조사",
            country_of_origin="대한민국",
        )
        db.add(product)
        db.flush()
        db.add(
            ProductRegistrationProfile(
                tenant_id=TENANT,
                product_id=product.id,
                primary_material="확정 재질",
                dimensions={"호스 외경": "8mm"},
                facts_confirmed=True,
                operating_info={"usage": "화분 관수"},
                marketing_info={"features": ["8mm 호스", "마이크로 스프레이"]},
            )
        )
        for length in ("10m", "20m", "30m"):
            db.add(
                ProductSKU(
                    tenant_id=TENANT,
                    product_id=product.id,
                    sku_code=f"IRRIGATION-8MM-{length.upper()}",
                    name=length,
                    option_value=length,
                    status="active",
                )
            )
        db.commit()
        product_id = product.id

    def db_override():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[content_copy.get_db] = db_override
    app.dependency_overrides[canva_controlled_export.get_db] = db_override
    app.dependency_overrides[require_business_auth] = lambda: None
    monkeypatch.setattr(
        content_copy,
        "generate_canva_v12_copy_candidates",
        lambda **_kwargs: (
            {"hero_headline": "필요한 곳에 정확하게 전달하는 물 관리"},
            {
                "provider": "openai-canva-copy-v1.2",
                "auto_saved": False,
                "auto_approved": False,
            },
        ),
    )

    client = TestClient(app)
    try:
        before = client.get(
            f"/api/v1/detail-page-canva/v1.2/products/{product_id}/draft",
            params={"tenant_id": TENANT},
        )
        assert before.status_code == 200
        before_data = before.json()
        assert before_data["text_fields"]["option_1_name"] == "10m"
        assert before_data["text_fields"]["option_2_name"] == "20m"
        assert before_data["text_fields"]["option_3_name"] == "30m"
        assert before_data["text_fields"]["hero_headline"] == ""

        proposed = client.post(
            f"/api/v1/content-copy/products/{product_id}/canva-v12/ai-candidates",
            params={"tenant_id": TENANT},
            json={"execution_approved": True},
        )
        assert proposed.status_code == 200
        assert proposed.json()["proposals"]["hero_headline"].startswith("필요한 곳에")
        assert proposed.json()["saved"] is False
        assert proposed.json()["approved"] is False
        with Session(engine) as db:
            assert db.scalar(select(func.count(ContentCopyAsset.id))) == 0

        saved = client.post(
            f"/api/v1/content-copy/products/{product_id}/assets",
            params={"tenant_id": TENANT},
            json={
                "target_type": "canva_v12",
                "slot_key": "hero_headline",
                "content": proposed.json()["proposals"]["hero_headline"],
                "source_fact_keys": ["confirmed_product_facts"],
                "generation_method": "ai_assisted",
            },
        )
        assert saved.status_code == 200
        asset_id = saved.json()["id"]

        candidate_draft = client.get(
            f"/api/v1/detail-page-canva/v1.2/products/{product_id}/draft",
            params={"tenant_id": TENANT},
        ).json()
        assert candidate_draft["text_fields"]["hero_headline"] == ""

        approved = client.post(
            f"/api/v1/content-copy/assets/{asset_id}/approval",
            params={"tenant_id": TENANT},
            json={"approved": True, "approved_by": "dashboard-user"},
        )
        assert approved.status_code == 200

        after = client.get(
            f"/api/v1/detail-page-canva/v1.2/products/{product_id}/draft",
            params={"tenant_id": TENANT},
        ).json()
        assert after["completed_count"] == before_data["completed_count"] + 1
        assert after["text_fields"]["hero_headline"].startswith("필요한 곳에")
    finally:
        app.dependency_overrides.clear()
