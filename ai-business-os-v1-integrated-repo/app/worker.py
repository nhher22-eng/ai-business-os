import os
import socket
import time
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.db.models import Run, RunStatus, WorkerHeartbeat
from app.services.queue import dequeue_run, enqueue_run

WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

MAX_ATTEMPTS = max(1, int(os.getenv("AIOS_RUN_MAX_ATTEMPTS", "3")))
FAILURE_INJECTION_ENABLED = (
    os.getenv("AIOS_ENABLE_FAILURE_INJECTION", "0") == "1"
)


def heartbeat():
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        hb = db.get(WorkerHeartbeat, WORKER_ID)

        if hb is None:
            hb = WorkerHeartbeat(
                worker_id=WORKER_ID,
                last_heartbeat_at=now,
            )
            db.add(hb)
        else:
            hb.last_heartbeat_at = now

        db.commit()


def execute(run: Run, attempt: int) -> str:
    # Test-only failure injection.
    # Disabled unless AIOS_ENABLE_FAILURE_INJECTION=1.
    if FAILURE_INJECTION_ENABLED:
        if run.task.startswith("PG_FAIL_ALWAYS:"):
            raise RuntimeError("Injected permanent failure for PG validation")

        if run.task.startswith("PG_RETRY_ONCE:") and attempt == 0:
            raise RuntimeError("Injected transient failure for PG validation")

    # Safe baseline executor: no external tool execution yet.
    return f"Processed by AI Business OS worker: {run.task}"


def process(run_id: str, attempt: int = 0):
    with SessionLocal() as db:
        run = db.get(Run, run_id)

        if not run:
            return

        run.status = RunStatus.running
        db.commit()

        try:
            run.result = execute(run, attempt)
            run.status = RunStatus.succeeded
            db.commit()

        except Exception as exc:
            error_text = f"{type(exc).__name__}: {str(exc)[:500]}"
            next_attempt = attempt + 1

            if next_attempt < MAX_ATTEMPTS:
                run.status = RunStatus.queued
                run.result = (
                    f"Retry scheduled after attempt "
                    f"{next_attempt}/{MAX_ATTEMPTS}: {error_text}"
                )
                db.commit()

                enqueue_run(
                    run.id,
                    attempt=next_attempt,
                )

                print(
                    f"run={run.id} retry={next_attempt} error={error_text}",
                    flush=True,
                )
                return

            run.status = RunStatus.failed
            run.result = (
                f"Failed after {MAX_ATTEMPTS} attempts: {error_text}"
            )
            db.commit()

            print(
                f"run={run.id} failed attempts={MAX_ATTEMPTS} "
                f"error={error_text}",
                flush=True,
            )


def main():
    while True:
        try:
            heartbeat()

            item = dequeue_run(timeout=2)

            if item:
                process(
                    item["run_id"],
                    int(item.get("attempt", 0)),
                )

        except Exception as exc:
            # One bad run or transient infrastructure error must not
            # terminate the long-lived worker process.
            print(
                f"worker_loop_error={type(exc).__name__}: {exc}",
                flush=True,
            )
            time.sleep(1)

        time.sleep(0.2)


if __name__ == "__main__":
    main()
