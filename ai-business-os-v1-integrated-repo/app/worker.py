import os
import socket
import time
from datetime import datetime, timezone
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models import Run, RunStatus, WorkerHeartbeat
from app.services.queue import dequeue_run

WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

def heartbeat():
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        hb = db.get(WorkerHeartbeat, WORKER_ID)
        if hb is None:
            hb = WorkerHeartbeat(worker_id=WORKER_ID, last_heartbeat_at=now)
            db.add(hb)
        else:
            hb.last_heartbeat_at = now
        db.commit()

def process(run_id: str):
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if not run:
            return
        run.status = RunStatus.running
        db.commit()

        # Safe baseline executor: no external tool execution yet.
        run.result = f"Processed by AI Business OS worker: {run.task}"
        run.status = RunStatus.succeeded
        db.commit()

def main():
    while True:
        heartbeat()
        item = dequeue_run(timeout=2)
        if item:
            process(item["run_id"])
        time.sleep(0.2)

if __name__ == "__main__":
    main()
