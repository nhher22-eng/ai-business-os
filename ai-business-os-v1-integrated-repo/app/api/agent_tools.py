from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import LEGACY_AGENT_ID, LEGACY_TENANT_ID, Run, RunStatus
from app.db.session import SessionLocal
from app.services.agent_control import authorize_identity
from app.services.agent_tools import MAX_STAGE_FILES, TOOL_PROTOCOL, TOOL_REGISTRY, build_plan, stage_file
from app.services.queue import enqueue_run


router = APIRouter(
    prefix="/api/v1/agent-tools",
    tags=["agent-tools"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ToolExecuteBody(BaseModel):
    action: str = Field(min_length=1, max_length=80)
    product_id: str | None = Field(default=None, max_length=36)
    category_query: str | None = Field(default=None, max_length=160)
    staged_attachment_ids: list[str] = Field(default_factory=list, max_length=10)
    args: dict = Field(default_factory=dict)
    approval_confirmed: bool = False
    tenant_id: str = Field(default=LEGACY_TENANT_ID, min_length=1, max_length=128)
    agent_id: str = Field(default=LEGACY_AGENT_ID, min_length=1, max_length=128)


@router.get("/registry")
def tool_registry():
    return {"protocol": TOOL_PROTOCOL, "tools": TOOL_REGISTRY}


@router.post("/plan")
async def plan_agent_request(
    request_text: str = Form(..., min_length=1, max_length=5000),
    workflow: str = Form(default="기존 상품 수정", max_length=80),
    tenant_id: str = Form(default=LEGACY_TENANT_ID, max_length=128),
    context_product_id: str | None = Form(default=None, max_length=36),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    if len(files) > MAX_STAGE_FILES:
        raise HTTPException(413, detail=f"첨부파일은 최대 {MAX_STAGE_FILES}개입니다.")
    staged = []
    try:
        for upload in files:
            staged.append(stage_file(
                tenant_id=tenant_id,
                filename=upload.filename or "image",
                content_type=upload.content_type,
                content=await upload.read(),
            ))
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    return build_plan(db, tenant_id=tenant_id, workflow=workflow,
                      request_text=request_text, staged=staged,
                      context_product_id=context_product_id)


@router.post("/execute")
def execute_agent_tool(body: ToolExecuteBody, db: Session = Depends(get_db)):
    if body.action not in TOOL_REGISTRY:
        raise HTTPException(422, detail="등록되지 않은 Agent 도구입니다.")
    tool = TOOL_REGISTRY[body.action]
    if tool["approval"] and not body.approval_confirmed:
        raise HTTPException(409, detail="이 변경은 최종 승인이 필요합니다.")
    if body.action != "category_products" and not body.product_id:
        raise HTTPException(422, detail="대상 상품을 먼저 확정해 주세요.")
    decision = authorize_identity(
        db, tenant_id=body.tenant_id, agent_id=body.agent_id, source="agent-tool-api",
    )
    if not decision.allowed:
        db.commit()
        raise HTTPException(409, detail={"code": decision.reason_code,
                                         "message": "Agent 실행 통제에 의해 차단되었습니다."})
    payload = {
        "protocol": TOOL_PROTOCOL, "action": body.action,
        "tenant_id": body.tenant_id, "agent_id": body.agent_id,
        "product_id": body.product_id, "category_query": body.category_query,
        "staged_attachment_ids": body.staged_attachment_ids,
        "args": body.args, "approval_confirmed": body.approval_confirmed,
    }
    run = Run(task=json.dumps(payload, ensure_ascii=False), status=RunStatus.queued,
              tenant_id=body.tenant_id, agent_id=body.agent_id)
    db.add(run)
    db.commit()
    db.refresh(run)
    enqueue_run(run.id)
    return {"id": run.id, "status": run.status, "action": body.action,
            "approval_confirmed": body.approval_confirmed}
