from __future__ import annotations

import re
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.core.config import settings
from app.db.google_drive import GoogleDriveConnection
from app.db.canva import CanvaConnection
from app.db.models import LEGACY_TENANT_ID
from app.db.service_management import ServiceManagementSetting
from app.db.session import SessionLocal


router = APIRouter(
    prefix="/api/v1/service-management",
    tags=["service-management"],
    dependencies=[Depends(require_business_auth)],
)

BILLING_STATUSES = {"confirmed", "attention", "manual_check", "not_applicable"}
SECRET_PATTERN = re.compile(
    r"(?i)(?:password|passwd|secret|api[_ -]?key|token|card(?: number)?|cvv)\s*[:=]|"
    r"sk-[a-z0-9_-]{12,}|gh[pousr]_[a-z0-9_]{20,}|AKIA[0-9A-Z]{16}|"
    r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY|\b(?:\d[ -]*?){13,19}\b"
)

SERVICE_CATALOG = {
    "openai": {
        "name": "OpenAI API", "purpose": "Agent 분석·콘텐츠·이미지 생성", "icon": "sparkles",
        "management_url": "https://platform.openai.com/settings/organization/general",
        "billing_url": "https://platform.openai.com/settings/organization/billing/overview",
        "usage_url": "https://platform.openai.com/usage",
        "features": ["상품정보 AI 제안", "이미지 기획·생성", "향후 외부 조사 비교", "문서 분석"],
    },
    "aws": {
        "name": "AWS", "purpose": "EC2·디스크·백업·네트워크", "icon": "server",
        "management_url": "https://console.aws.amazon.com/ec2/",
        "billing_url": "https://console.aws.amazon.com/billing/home",
        "usage_url": "https://console.aws.amazon.com/cost-management/home",
        "features": ["AI Business OS 서버", "PostgreSQL·Redis", "백업", "운영 네트워크"],
    },
    "google_drive": {
        "name": "Google Drive", "purpose": "상품 이미지·문서 저장", "icon": "hard-drive",
        "management_url": "https://drive.google.com/drive/my-drive",
        "billing_url": "https://one.google.com/storage",
        "usage_url": "https://one.google.com/storage",
        "reauth_url": "/google-drive",
        "features": ["상품 원본 이미지", "등록 문서", "상품별 자산 폴더", "Agent 첨부자료"],
    },
    "canva": {
        "name": "Canva", "purpose": "상세페이지 템플릿·이미지·Autofill 생성", "icon": "layout",
        "management_url": "https://www.canva.com/developers/integrations",
        "billing_url": "https://www.canva.com/settings/billing-and-plans",
        "usage_url": "https://www.canva.com/projects",
        "reauth_url": "#connect-canva",
        "features": ["v1.2 브랜드 템플릿", "승인 이미지 업로드", "94필드 Autofill", "생성 디자인 확인"],
    },
    "github": {
        "name": "GitHub", "purpose": "코드 저장·배포 이력", "icon": "git-branch",
        "management_url": "https://github.com/settings/profile",
        "billing_url": "https://github.com/settings/billing/summary",
        "usage_url": "https://github.com/settings/billing/summary",
        "features": ["소스 저장", "기능 브랜치", "배포 이력", "복구 기준점"],
    },
    "naver": {
        "name": "네이버 Commerce API", "purpose": "상품·주문·판매채널 연동", "icon": "shopping-bag",
        "management_url": "https://apicenter.commerce.naver.com/",
        "billing_url": None, "usage_url": "https://apicenter.commerce.naver.com/",
        "features": ["판매채널 연결", "상품 등록 상태", "향후 주문 조회"],
    },
    "notifications": {
        "name": "운영 알림", "purpose": "SNS·이메일 장애 및 예산 알림", "icon": "mail",
        "management_url": "https://console.aws.amazon.com/sns/",
        "billing_url": "https://console.aws.amazon.com/billing/home",
        "usage_url": "https://console.aws.amazon.com/cost-management/home",
        "features": ["장애 알림", "백업 알림", "향후 예산 경고"],
    },
    "domain": {
        "name": "도메인·SSL", "purpose": "os.gardenfarm.kr 서비스 접속", "icon": "globe",
        "management_url": "https://my.gabia.com/",
        "billing_url": "https://my.gabia.com/",
        "usage_url": None,
        "features": ["서비스 도메인", "HTTPS 접속", "인증서 갱신"],
    },
    "market_research": {
        "name": "외부 시장조사", "purpose": "가격·경쟁상품·시장자료 검색", "icon": "search",
        "management_url": None, "billing_url": None, "usage_url": None,
        "features": ["온라인 가격 비교", "경쟁상품 조사", "시장 동향"],
    },
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ServiceSettingBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_name: str | None = Field(default=None, max_length=160)
    billing_status: str = Field(default="manual_check", max_length=32)
    current_month_cost_krw: int | None = Field(default=None, ge=0, le=1_000_000_000)
    monthly_budget_krw: int | None = Field(default=None, ge=0, le=1_000_000_000)
    renewal_date: date | None = None
    usage_summary: str | None = Field(default=None, max_length=240)
    note: str | None = Field(default=None, max_length=1000)
    updated_by: str = Field(default="dashboard-user", min_length=1, max_length=128)

    @field_validator("billing_status")
    @classmethod
    def valid_billing_status(cls, value: str) -> str:
        if value not in BILLING_STATUSES:
            raise ValueError("unsupported billing status")
        return value

    @field_validator("plan_name", "usage_summary", "note")
    @classmethod
    def reject_secrets(cls, value: str | None) -> str | None:
        cleaned = value.strip() if value else None
        if cleaned and SECRET_PATTERN.search(cleaned):
            raise ValueError("비밀번호·카드번호·API 키·토큰은 저장할 수 없습니다.")
        return cleaned


def _automatic_state(db: Session, tenant_id: str, code: str) -> dict:
    if code == "openai":
        configured = bool(settings.openai_api_key)
        return {
            "connection_status": "normal" if configured else "not_connected",
            "connection_label": "API 설정됨" if configured else "API 미설정",
            "auth_status": "registered" if configured else "missing",
            "auth_label": "API 키 등록됨" if configured else "API 키 없음",
            "check_method": "설정 자동 확인",
        }
    if code == "google_drive":
        row = db.scalar(select(GoogleDriveConnection).where(
            GoogleDriveConnection.tenant_id == tenant_id,
        ))
        connected = bool(row and row.root_folder_id and row.access_token_encrypted)
        expired_without_refresh = bool(
            connected and row.token_expires_at
            and row.token_expires_at <= datetime.now(timezone.utc)
            and not row.refresh_token_encrypted
        )
        return {
            "connection_status": "attention" if expired_without_refresh else ("normal" if connected else "not_connected"),
            "connection_label": "재인증 필요" if expired_without_refresh else ("연결됨" if connected else "미연결"),
            "auth_status": "renew" if expired_without_refresh else ("registered" if connected else "missing"),
            "auth_label": "OAuth 재인증 필요" if expired_without_refresh else ("OAuth 등록됨" if connected else "OAuth 미연결"),
            "check_method": "OAuth 상태 자동 확인",
        }
    if code == "canva":
        row = db.scalar(select(CanvaConnection).where(CanvaConnection.tenant_id == tenant_id))
        configured = bool(settings.canva_client_id and settings.canva_client_secret)
        connected = bool(configured and row and row.status == "connected")
        renewal = bool(row and row.status == "reauthorization_required")
        return {
            "connection_status": "attention" if renewal else ("normal" if connected else "not_connected"),
            "connection_label": "재인증 필요" if renewal else ("연결됨" if connected else ("앱 설정 필요" if not configured else "미연결")),
            "auth_status": "renew" if renewal else ("registered" if connected else "missing"),
            "auth_label": "OAuth 재인증 필요" if renewal else ("OAuth 등록됨" if connected else "OAuth 미연결"),
            "check_method": "OAuth·PKCE 상태 자동 확인",
        }
    if code == "market_research":
        return {"connection_status": "not_connected", "connection_label": "도입 전",
                "auth_status": "not_applicable", "auth_label": "연결 도구 미선정",
                "check_method": "구현 상태 확인"}
    if code == "naver":
        return {"connection_status": "not_connected", "connection_label": "미연결",
                "auth_status": "missing", "auth_label": "자격증명 미등록",
                "check_method": "연결 설정 확인"}
    if code == "aws":
        return {"connection_status": "normal", "connection_label": "OS 운영 중",
                "auth_status": "protected", "auth_label": "서버 권한 비공개",
                "check_method": "현재 서비스 실행 상태"}
    return {"connection_status": "manual", "connection_label": "수동 확인",
            "auth_status": "protected", "auth_label": "비밀정보 비공개",
            "check_method": "수동 확인"}


def _payload(db: Session, tenant_id: str, code: str,
             saved: ServiceManagementSetting | None) -> dict:
    catalog = SERVICE_CATALOG[code]
    automatic = _automatic_state(db, tenant_id, code)
    return {
        "code": code, **catalog, **automatic,
        "plan_name": saved.plan_name if saved else None,
        "billing_status": saved.billing_status if saved else "manual_check",
        "current_month_cost_krw": saved.current_month_cost_krw if saved else None,
        "monthly_budget_krw": saved.monthly_budget_krw if saved else None,
        "renewal_date": saved.renewal_date.isoformat() if saved and saved.renewal_date else None,
        "usage_summary": saved.usage_summary if saved else None,
        "note": saved.note if saved else None,
        "updated_by": saved.updated_by if saved else None,
        "updated_at": saved.updated_at.isoformat() if saved else None,
        "secrets_exposed": False,
        "payment_execution_allowed": False,
        "plan_change_allowed": False,
    }


@router.get("/services")
def list_services(tenant_id: str = Query(default=LEGACY_TENANT_ID, max_length=128),
                  db: Session = Depends(get_db)):
    rows = list(db.scalars(select(ServiceManagementSetting).where(
        ServiceManagementSetting.tenant_id == tenant_id,
    )).all())
    saved = {row.service_code: row for row in rows}
    services = [_payload(db, tenant_id, code, saved.get(code)) for code in SERVICE_CATALOG]
    total_cost = sum(row["current_month_cost_krw"] or 0 for row in services)
    total_budget = sum(row["monthly_budget_krw"] or 0 for row in services)
    attention = sum(
        row["connection_status"] in {"attention", "not_connected"}
        or row["billing_status"] == "attention"
        for row in services
    )
    return {
        "services": services,
        "summary": {
            "service_count": len(services), "attention_count": attention,
            "current_month_cost_krw": total_cost,
            "monthly_budget_krw": total_budget,
            "budget_usage_percent": round(total_cost / total_budget * 100, 1) if total_budget else None,
        },
        "security": {
            "secrets_returned": False,
            "external_payment_execution": False,
            "external_plan_change": False,
            "official_console_handoff": True,
        },
    }


@router.put("/services/{service_code}")
def save_service_setting(service_code: str, body: ServiceSettingBody,
                         tenant_id: str = Query(default=LEGACY_TENANT_ID, max_length=128),
                         db: Session = Depends(get_db)):
    if service_code not in SERVICE_CATALOG:
        raise HTTPException(404, "등록되지 않은 서비스입니다.")
    row = db.scalar(select(ServiceManagementSetting).where(
        ServiceManagementSetting.tenant_id == tenant_id,
        ServiceManagementSetting.service_code == service_code,
    ))
    if row is None:
        row = ServiceManagementSetting(tenant_id=tenant_id, service_code=service_code)
        db.add(row)
    for field, value in body.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return {"saved": True, "service": _payload(db, tenant_id, service_code, row)}
