from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.db.models import ImageGenerationJob
from app.db.session import SessionLocal
from app.services.image_studio import ImageStudioError, ProviderNotConfigured, generate_stage

POLL_SECONDS = max(0.2, float(os.getenv("AIOS_IMAGE_WORKER_POLL_SECONDS", "1.0")))
STALE_SECONDS = max(300, int(os.getenv("AIOS_IMAGE_FINAL_STALE_SECONDS", "900")))
RECOVERY_INTERVAL = 60.0


def recover_stale_generations() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=STALE_SECONDS)
    with SessionLocal() as db:
        result = db.execute(
            update(ImageGenerationJob)
            .where(
                ImageGenerationJob.status == "final_generating",
                ImageGenerationJob.updated_at < cutoff,
            )
            .values(status="final_queued")
        )
        db.commit()
        return int(result.rowcount or 0)


def claim_next_job() -> str | None:
    with SessionLocal() as db:
        job = db.scalar(
            select(ImageGenerationJob)
            .where(ImageGenerationJob.status == "final_queued")
            .order_by(ImageGenerationJob.updated_at, ImageGenerationJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        job.status = "final_generating"
        db.commit()
        return job.id


def process_job(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.get(ImageGenerationJob, job_id)
        if job is None or job.status != "final_generating":
            return
        try:
            asset = generate_stage(db, job, "final")
            print(
                f"image_final job={job.id} asset={asset.id} version={asset.version_no} status={job.status}",
                flush=True,
            )
        except (ProviderNotConfigured, ImageStudioError) as exc:
            # generate_stage records provider/runtime failures as failed where appropriate.
            job = db.get(ImageGenerationJob, job_id)
            if job is not None and job.status == "final_generating":
                job.status = "failed"
                db.commit()
            print(f"image_final_failed job={job_id} error={type(exc).__name__}: {exc}", flush=True)
        except Exception as exc:
            job = db.get(ImageGenerationJob, job_id)
            if job is not None and job.status == "final_generating":
                job.status = "failed"
                db.commit()
            print(f"image_final_failed job={job_id} error={type(exc).__name__}: {exc}", flush=True)


def main() -> None:
    last_recovery = 0.0
    while True:
        try:
            now = time.monotonic()
            if now - last_recovery >= RECOVERY_INTERVAL:
                recovered = recover_stale_generations()
                if recovered:
                    print(f"image_final_recovered count={recovered}", flush=True)
                last_recovery = now

            job_id = claim_next_job()
            if job_id:
                process_job(job_id)
                continue
        except Exception as exc:
            print(f"image_worker_loop_error={type(exc).__name__}: {exc}", flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
