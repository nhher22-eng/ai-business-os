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
SUGGESTION_CREATED_BY_PREFIX = "product-registration-ai-suggestion:"


def recover_stale_generations() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=STALE_SECONDS)
    with SessionLocal() as db:
        final_result = db.execute(
            update(ImageGenerationJob)
            .where(
                ImageGenerationJob.status == "final_generating",
                ImageGenerationJob.updated_at < cutoff,
            )
            .values(status="final_queued")
        )
        suggestion_result = db.execute(
            update(ImageGenerationJob)
            .where(
                ImageGenerationJob.status == "suggestion_generating",
                ImageGenerationJob.updated_at < cutoff,
                ImageGenerationJob.created_by.like(SUGGESTION_CREATED_BY_PREFIX + "%"),
            )
            .values(status="suggestion_queued")
        )
        db.commit()
        return int(final_result.rowcount or 0) + int(suggestion_result.rowcount or 0)


def claim_next_job() -> tuple[str, str] | None:
    with SessionLocal() as db:
        job = db.scalar(
            select(ImageGenerationJob)
            .where(
                ImageGenerationJob.status.in_(["final_queued", "suggestion_queued"])
            )
            .order_by(ImageGenerationJob.updated_at, ImageGenerationJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None

        kind = "suggestion" if job.status == "suggestion_queued" else "final"
        job.status = "suggestion_generating" if kind == "suggestion" else "final_generating"
        db.commit()
        return job.id, kind


def process_job(job_id: str, kind: str) -> None:
    with SessionLocal() as db:
        job = db.get(ImageGenerationJob, job_id)
        expected = "suggestion_generating" if kind == "suggestion" else "final_generating"
        if job is None or job.status != expected:
            return
        try:
            stage = "preview" if kind == "suggestion" else "final"
            asset = generate_stage(db, job, stage)
            if kind == "suggestion":
                job = db.get(ImageGenerationJob, job_id)
                if job is not None and job.status == "preview_review":
                    job.status = "suggestion_review"
                    db.commit()
            print(
                f"image_{kind} job={job_id} asset={asset.id} version={asset.version_no}",
                flush=True,
            )
        except (ProviderNotConfigured, ImageStudioError) as exc:
            job = db.get(ImageGenerationJob, job_id)
            if job is not None and job.status in {expected, "failed"}:
                job.status = "failed"
                db.commit()
            print(
                f"image_{kind}_failed job={job_id} error={type(exc).__name__}: {exc}",
                flush=True,
            )
        except Exception as exc:
            job = db.get(ImageGenerationJob, job_id)
            if job is not None and job.status == expected:
                job.status = "failed"
                db.commit()
            print(
                f"image_{kind}_failed job={job_id} error={type(exc).__name__}: {exc}",
                flush=True,
            )


def main() -> None:
    last_recovery = 0.0
    while True:
        try:
            now = time.monotonic()
            if now - last_recovery >= RECOVERY_INTERVAL:
                recovered = recover_stale_generations()
                if recovered:
                    print(f"image_generation_recovered count={recovered}", flush=True)
                last_recovery = now

            claimed = claim_next_job()
            if claimed:
                process_job(*claimed)
                continue
        except Exception as exc:
            print(f"image_worker_loop_error={type(exc).__name__}: {exc}", flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
