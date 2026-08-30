from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.models import (
    LEGACY_AGENT_ID,
    LEGACY_TENANT_ID,
    Run,
    RunStatus,
)
from app.db.session import SessionLocal
from app.services.agent_control import authorize_identity
from app.services.queue import enqueue_run


router = APIRouter(
    prefix="/api/v1/runs",
    tags=["runs"],
)


class RunCreate(BaseModel):
    task: str = Field(
        min_length=1,
        max_length=10000,
    )
    tenant_id: str = Field(
        default=LEGACY_TENANT_ID,
        min_length=1,
        max_length=128,
    )
    agent_id: str = Field(
        default=LEGACY_AGENT_ID,
        min_length=1,
        max_length=128,
    )


@router.post("")
def create_run(payload: RunCreate):
    with SessionLocal() as db:
        decision = authorize_identity(
            db,
            tenant_id=payload.tenant_id,
            agent_id=payload.agent_id,
            source="api",
        )

        if not decision.allowed:
            db.commit()
            raise HTTPException(
                status_code=409,
                detail={
                    "code": decision.reason_code,
                    "message": (
                        "run blocked by automation control"
                    ),
                },
            )

        run = Run(
            task=payload.task,
            status=RunStatus.queued,
            tenant_id=payload.tenant_id,
            agent_id=payload.agent_id,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        enqueue_run(run.id)

        return {
            "id": run.id,
            "status": run.status,
            "task": run.task,
            "tenant_id": run.tenant_id,
            "agent_id": run.agent_id,
        }


@router.get("/{run_id}")
def get_run(run_id: str):
    with SessionLocal() as db:
        run = db.get(Run, run_id)

        if not run:
            raise HTTPException(
                status_code=404,
                detail="run not found",
            )

        return {
            "id": run.id,
            "task": run.task,
            "status": run.status,
            "result": run.result,
            "tenant_id": run.tenant_id,
            "agent_id": run.agent_id,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
        }
