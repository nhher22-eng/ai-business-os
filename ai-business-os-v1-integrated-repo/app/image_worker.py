from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.db.models import ImageGenerationJob
from app.db.product_image_fact import ProductImageFact
from app.db.session import SessionLocal
from app.services.image_studio import ImageStudioError, ProviderNotConfigured, generate_stage
from app.services.product_image_fact import ProductImageFactError, apply_slot_policy, classify_slot, process_row
from app.services.image_studio import resolve_media_uri

POLL_SECONDS = max(0.2, float(os.getenv("AIOS_IMAGE_WORKER_POLL_SECONDS", "1.0")))
STALE_SECONDS = max(300, int(os.getenv("AIOS_IMAGE_FINAL_STALE_SECONDS", "900")))
RECOVERY_INTERVAL = 60.0


def recover_stale_generations() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=STALE_SECONDS)
    with SessionLocal() as db:
        result = db.execute(
            update(ImageGenerationJob)
            .where(ImageGenerationJob.status == "final_generating", ImageGenerationJob.updated_at < cutoff)
            .values(status="final_queued")
        )
        db.commit()
        return int(result.rowcount or 0)


def recover_stale_product_facts() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=STALE_SECONDS)
    with SessionLocal() as db:
        result = db.execute(
            update(ProductImageFact)
            .where(ProductImageFact.status == "processing", ProductImageFact.updated_at < cutoff)
            .values(status="processing_queued")
        )
        db.commit()
        return int(result.rowcount or 0)


def claim_next_product_fact() -> str | None:
    with SessionLocal() as db:
        row = db.scalar(
            select(ProductImageFact)
            .where(ProductImageFact.status == "processing_queued")
            .order_by(ProductImageFact.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if row is None:
            return None
        row.status = "processing"
        db.commit()
        return row.id


def process_product_fact(image_fact_id: str) -> None:
    with SessionLocal() as db:
        row = db.get(ProductImageFact, image_fact_id)
        if row is None or row.status != "processing":
            return
        try:
            if not row.raw_asset_uri:
                raise ProductImageFactError("임시 촬영 원본이 없습니다.")
            raw_path = resolve_media_uri(row.raw_asset_uri)
            content = raw_path.read_bytes()
            slot, source, confidence = classify_slot(
                filename=row.original_filename or "product-image",
                mime_type=row.mime_type,
                content=content,
            )
            row.classification_source = source
            row.classification_confidence = confidence
            apply_slot_policy(row, slot)
            if slot == "UNASSIGNED":
                row.status = "needs_review"
            else:
                process_row(row)
            db.commit()
            print(f"product_image_fact id={row.id} slot={row.slot_type} status={row.status}", flush=True)
        except Exception as exc:
            row = db.get(ProductImageFact, image_fact_id)
            if row is not None:
                row.status = "needs_review"
                row.notes = f"processing_error:{type(exc).__name__}:{str(exc)[:500]}"
                db.commit()
            print(f"product_image_fact_failed id={image_fact_id} error={type(exc).__name__}: {exc}", flush=True)


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
            print(f"image_final job={job.id} asset={asset.id} version={asset.version_no} status={job.status}", flush=True)
        except (ProviderNotConfigured, ImageStudioError) as exc:
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
                recovered_facts = recover_stale_product_facts()
                if recovered:
                    print(f"image_final_recovered count={recovered}", flush=True)
                if recovered_facts:
                    print(f"product_image_fact_recovered count={recovered_facts}", flush=True)
                last_recovery = now

            fact_id = claim_next_product_fact()
            if fact_id:
                process_product_fact(fact_id)
                continue

            job_id = claim_next_job()
            if job_id:
                process_job(job_id)
                continue
        except Exception as exc:
            print(f"image_worker_loop_error={type(exc).__name__}: {exc}", flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
