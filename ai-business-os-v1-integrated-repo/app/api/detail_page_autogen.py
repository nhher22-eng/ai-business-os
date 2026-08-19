from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.session import SessionLocal
from app.services.detail_page_autogen import auto_generate_release_candidate


router = APIRouter(
    prefix="/api/v1/detail-page-autogen",
    tags=["detail-page-autogen"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AutoGenerateBody(BaseModel):
    workspace_id: str
    product_id: str
    channel: str = "naver-smartstore"
    page_length: Literal["long", "short"] = "long"
    template_code: str = "A_PRACTICAL_TRUST"
    visual_style: str = "natural"
    page_strategy: str = "standard"
    brand_style_sheet_id: str | None = None
    created_by: str | None = None


@router.post("/generate")
def generate_release_candidate(
    body: AutoGenerateBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    try:
        result = auto_generate_release_candidate(
            db,
            tenant_id=tenant_id,
            workspace_id=body.workspace_id,
            product_id=body.product_id,
            channel=body.channel,
            page_length=body.page_length,
            template_code=body.template_code,
            visual_style=body.visual_style,
            page_strategy=body.page_strategy,
            brand_style_sheet_id=body.brand_style_sheet_id,
            created_by=body.created_by,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return {
        "pipeline": "m06.detail-page-autogen.v1",
        "job_id": result.job.id,
        "version_id": result.version.id,
        "version_no": result.version.version_no,
        "status": result.job.status,
        "qa_summary": result.qa_summary,
        "release_ready": result.release_ready,
        "enabled_sections": result.enabled_sections,
        "hidden_sections": result.hidden_sections,
        "qa": [
            {
                "check_code": row.check_code,
                "status": row.status,
                "severity": row.severity,
                "message": row.message,
                "suggested_fix": row.suggested_fix,
            }
            for row in result.qa_rows
        ],
        "next_action": (
            "human_approval_then_canva_export"
            if result.qa_summary == "PASS"
            else "resolve_review_or_fail_items"
        ),
    }
