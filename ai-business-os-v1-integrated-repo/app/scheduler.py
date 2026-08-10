import time
from datetime import datetime, timezone
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models import ScheduledJob

def tick():
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        jobs = db.scalars(
            select(ScheduledJob).where(
                ScheduledJob.scheduled_at <= now,
                ScheduledJob.status == "pending",
            )
        ).all()
        for job in jobs:
            job.started_at = now
            job.status = "completed"
        db.commit()

def main():
    while True:
        tick()
        time.sleep(settings.scheduler_interval_seconds)

if __name__ == "__main__":
    main()
