import importlib

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dashboard_session import require_business_auth
from app.api.service_management import get_db, router as service_management_router
from app.core.config import settings
from app.db.google_drive import GoogleDriveConnection
from app.db.canva import CanvaConnection
from app.db.models import Base
from app.global_navigation import NAV_CONTENT
from app.service_management_ui import HTML, router as service_management_ui_router


def _client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)

    def override_db():
        yield db

    test_app = FastAPI()
    test_app.include_router(service_management_router)
    test_app.include_router(service_management_ui_router)
    test_app.dependency_overrides[require_business_auth] = lambda: None
    test_app.dependency_overrides[get_db] = override_db
    return TestClient(test_app), db, test_app


def test_service_management_reports_real_configuration_without_secrets(monkeypatch):
    client, db, test_app = _client()
    monkeypatch.setattr(settings, "openai_api_key", "configured-but-never-returned")
    db.add(GoogleDriveConnection(
        tenant_id="__legacy__", root_folder_id="root",
        access_token_encrypted="encrypted", refresh_token_encrypted="encrypted-refresh",
        folder_map={"products": "folder"},
    ))
    db.commit()
    try:
        response = client.get("/api/v1/service-management/services")
        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["service_count"] == 9
        by_code = {row["code"]: row for row in payload["services"]}
        assert by_code["openai"]["connection_label"] == "API 설정됨"
        assert by_code["google_drive"]["connection_label"] == "연결됨"
        assert by_code["canva"]["connection_label"] in {"앱 설정 필요", "미연결"}
        assert by_code["canva"]["reauth_url"] == "#connect-canva"
        assert by_code["market_research"]["connection_label"] == "도입 전"
        assert by_code["openai"]["secrets_exposed"] is False
        assert "configured-but-never-returned" not in response.text
        assert payload["security"]["external_payment_execution"] is False
    finally:
        test_app.dependency_overrides.clear()
        db.close()


def test_non_secret_billing_metadata_is_saved_and_summarized():
    client, db, test_app = _client()
    try:
        response = client.put(
            "/api/v1/service-management/services/openai",
            json={
                "plan_name": "사용량 과금", "billing_status": "confirmed",
                "current_month_cost_krw": 18400, "monthly_budget_krw": 30000,
                "renewal_date": "2026-09-01", "usage_summary": "월 한도의 62%",
                "note": "월말 사용량 확인", "updated_by": "dashboard-user",
            },
        )
        assert response.status_code == 200
        assert response.json()["service"]["current_month_cost_krw"] == 18400
        listed = client.get("/api/v1/service-management/services").json()
        assert listed["summary"]["current_month_cost_krw"] == 18400
        assert listed["summary"]["monthly_budget_krw"] == 30000
        assert listed["summary"]["budget_usage_percent"] == 61.3
    finally:
        test_app.dependency_overrides.clear()
        db.close()


def test_secret_like_values_are_rejected_and_unknown_services_are_not_created():
    client, db, test_app = _client()
    try:
        secret = client.put(
            "/api/v1/service-management/services/openai",
            json={"billing_status": "manual_check", "note": "api_key=example-sensitive-value"},
        )
        assert secret.status_code == 422
        unknown = client.put(
            "/api/v1/service-management/services/not-real",
            json={"billing_status": "manual_check"},
        )
        assert unknown.status_code == 404
        injected_link = client.put(
            "/api/v1/service-management/services/openai",
            json={"billing_status": "manual_check", "management_url": "https://evil.example"},
        )
        assert injected_link.status_code == 422
    finally:
        test_app.dependency_overrides.clear()
        db.close()


def test_ui_matches_approved_visual_and_official_handoff_boundary():
    assert "서비스·연결·요금 관리" in HTML
    assert "전체 상태 확인" in HTML
    assert "결제 관리" in HTML
    assert "사용량 확인" in HTML
    assert "재인증" in HTML
    assert "비밀번호·카드번호·API 키·토큰" in HTML
    assert "결제와 요금제 변경은 Agent가 수행하지 않으며" in HTML
    assert 'rel="noopener noreferrer"' in HTML
    assert 'href="/service-management"' in NAV_CONTENT
    assert "/api/v1/integrations/canva/connect" in HTML
    assert "method:'POST'" in HTML


def test_service_management_migration_follows_current_head():
    migration = importlib.import_module(
        "migrations.versions.0019_service_management_settings"
    )
    assert migration.down_revision == "0018_approved_product_ui"
    assert migration.revision == "0019_service_management"


def test_service_management_migration_creates_expected_table():
    migration = importlib.import_module(
        "migrations.versions.0019_service_management_settings"
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        columns = {row["name"] for row in inspect(connection).get_columns(
            "service_management_settings"
        )}
        assert {"service_code", "billing_status", "monthly_budget_krw", "renewal_date"} <= columns
