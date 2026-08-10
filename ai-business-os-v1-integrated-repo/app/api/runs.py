from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db.session import SessionLocal
from app.db.models import Run, RunStatus
from app.services.queue import enqueue_run

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])

class RunCreate(BaseModel):
    task: str = Field(min_length=1, max_length=10000)

@router.post("")
def create_run(payload: RunCreate):
    with SessionLocal() as db:
        run = Run(task=payload.task, status=RunStatus.queued)
        db.add(run)
        db.commit()
        db.refresh(run)
        enqueue_run(run.id)
        return {"id": run.id, "status": run.status, "task": run.task}

@router.get("/{run_id}")
def get_run(run_id: str):
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="run not found")
        return {
            "id": run.id,
            "task": run.task,
            "status": run.status,
            "result": run.result,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
        }
