import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

from app.db.models import ScheduledJob, WebhookOutbox, WorkerHeartbeat
from app.db.session import SessionLocal
from app.services.queue import queue_depth


def utcnow():
    return datetime.now(timezone.utc)


def as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def probe(name, status, details):
    return {"name": name, "status": status, "details": details}


def main():
    parser = argparse.ArgumentParser(description="HP-02 live monitoring gate")
    parser.add_argument("--output", default=os.getenv("HP02_EVIDENCE_PATH", ""))
    args = parser.parse_args()

    worker_max_age = float(os.getenv("HP02_WORKER_MAX_AGE_SECONDS", "60"))
    backlog_warn = int(os.getenv("HP02_QUEUE_BACKLOG_WARN", "100"))
    dead_statuses = {x.strip().lower() for x in os.getenv(
        "HP02_WEBHOOK_DEAD_STATUSES", "dead,dead_letter,dead-letter"
    ).split(",") if x.strip()}

    now = utcnow()
    probes = []

    try:
        with SessionLocal() as db:
            latest_hb = as_utc(db.scalar(select(func.max(WorkerHeartbeat.last_heartbeat_at))))
            if latest_hb is None:
                probes.append(probe("worker_heartbeat", "FAIL", {"reason": "no heartbeat rows"}))
            else:
                age = max(0.0, (now - latest_hb).total_seconds())
                probes.append(probe(
                    "worker_heartbeat",
                    "PASS" if age <= worker_max_age else "FAIL",
                    {"age_seconds": round(age, 3), "max_age_seconds": worker_max_age},
                ))

            overdue = int(db.scalar(
                select(func.count()).select_from(ScheduledJob).where(
                    ScheduledJob.status == "pending",
                    ScheduledJob.scheduled_at <= now,
                )
            ) or 0)
            probes.append(probe(
                "scheduler_overdue",
                "PASS" if overdue == 0 else "FAIL",
                {"overdue_pending_jobs": overdue},
            ))

            statuses = db.scalars(select(WebhookOutbox.status)).all()
            dead_count = sum(1 for status in statuses if (status or "").lower() in dead_statuses)
            probes.append(probe(
                "webhook_dead_letters",
                "PASS" if dead_count == 0 else "FAIL",
                {"dead_letter_count": dead_count, "dead_statuses": sorted(dead_statuses)},
            ))
    except Exception as exc:
        probes.append(probe(
            "database_probes", "FAIL",
            {"error": f"{type(exc).__name__}: {str(exc)[:300]}"},
        ))

    try:
        depth = queue_depth()
        probes.append(probe(
            "queue_backlog",
            "WARN" if depth > backlog_warn else "PASS",
            {"queue_depth": depth, "warn_threshold": backlog_warn},
        ))
    except Exception as exc:
        probes.append(probe(
            "queue_backlog", "FAIL",
            {"error": f"{type(exc).__name__}: {str(exc)[:300]}"},
        ))

    probes.append(probe(
        "queue_stale_leases",
        "WARN",
        {"reason": "lease model is not implemented; queue uses Redis BLPOP"},
    ))

    failed = any(p["status"] == "FAIL" for p in probes)
    overall = "FAIL" if failed else ("WARN" if any(p["status"] == "WARN" for p in probes) else "PASS")
    evidence = {
        "gate": "HP-02",
        "mode": "live",
        "checked_at": now.isoformat(),
        "overall": overall,
        "probes": probes,
    }

    payload = json.dumps(evidence, ensure_ascii=False, indent=2)
    print(payload)

    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n", encoding="utf-8")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
