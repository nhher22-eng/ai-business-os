from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import content_copy
from app.api.dashboard_session import require_business_auth
from app.db.content_copy import ContentCopyAsset
from app.db.models import Base, BusinessWorkspace, Product
from app.db.product_registration import ProductRegistrationProfile


TENANT = "content-copy-test"


def test_candidate_save_and_approval_flow():
    app = FastAPI()
    app.include_router(content_copy.router)
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        workspace = BusinessWorkspace(
            tenant_id=TENANT,
            name="Copy Workspace",
            slug="copy-workspace",
            business_type="commerce",
            mode="shadow",
        )
        db.add(workspace)
        db.flush()
        product = Product(
            tenant_id=TENANT,
            workspace_id=workspace.id,
            product_code="COPY-001",
            name="8 mm 자동 관수키트",
            description="화분에 물을 공급하는 관수키트",
        )
        db.add(product)
        db.flush()
        db.add(
            ProductRegistrationProfile(
                tenant_id=TENANT,
                product_id=product.id,
                primary_material="플라스틱",
                dimensions={"hose": "10 m"},
                facts_confirmed=True,
                additional_image_asset_ids=[],
                operating_info={"usage": "화분 자동 관수"},
                marketing_info={"features": ["8 mm 호스", "마이크로 스프레이"]},
            )
        )
        db.commit()
        product_id = product.id

    def db_override():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[content_copy.get_db] = db_override
    app.dependency_overrides[require_business_auth] = lambda: None
    client = TestClient(app)
    try:
        response = client.get(
            f"/api/v1/content-copy/products/{product_id}/candidates",
            params={"tenant_id": TENANT, "target_type": "detail_page"},
        )
        assert response.status_code == 200
        candidate = next(x for x in response.json()["slots"] if x["slot_key"] == "specification")
        assert "10 m" in candidate["content"]
        assert candidate["generation_method"] == "fact_substitution"

        response = client.post(
            f"/api/v1/content-copy/products/{product_id}/assets",
            params={"tenant_id": TENANT},
            json={
                "target_type": "detail_page",
                "slot_key": "specification",
                "content": candidate["content"],
                "source_fact_keys": candidate["source_fact_keys"],
                "generation_method": candidate["generation_method"],
            },
        )
        assert response.status_code == 200
        asset_id = response.json()["id"]
        assert response.json()["status"] == "candidate"

        response = client.post(
            f"/api/v1/content-copy/assets/{asset_id}/approval",
            params={"tenant_id": TENANT},
            json={"approved": True, "approved_by": "reviewer"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "approved"
        assert response.json()["approved_by"] == "reviewer"

        response = client.get(
            f"/api/v1/content-copy/products/{product_id}/assets",
            params={"tenant_id": TENANT, "status": "approved"},
        )
        assert response.status_code == 200
        assert [x["id"] for x in response.json()] == [asset_id]
    finally:
        app.dependency_overrides.clear()
