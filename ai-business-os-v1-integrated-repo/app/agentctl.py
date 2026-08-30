import argparse

from app.db.models import (
    LEGACY_AGENT_ID,
    LEGACY_TENANT_ID,
)
from app.db.session import SessionLocal
from app.services.agent_control import (
    get_agent_state,
    is_tenant_paused,
    set_agent_state,
    set_tenant_paused,
)


def main():
    parser = argparse.ArgumentParser(
        description="AI Business OS Agent Control"
    )
    parser.add_argument(
        "command",
        choices=[
            "status",
            "on",
            "pause",
            "off",
            "pause-all",
            "resume-all",
        ],
    )
    parser.add_argument(
        "--tenant",
        default=LEGACY_TENANT_ID,
    )
    parser.add_argument(
        "--agent",
        default=LEGACY_AGENT_ID,
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.command == "status":
            print(f"tenant={args.tenant}")
            print(
                f"tenant_paused="
                f"{is_tenant_paused(db, args.tenant)}"
            )
            print(f"agent={args.agent}")
            print(
                f"desired_state="
                f"{get_agent_state(db, args.tenant, args.agent)}"
            )
            return

        if args.command in {"on", "pause", "off"}:
            set_agent_state(
                db,
                tenant_id=args.tenant,
                agent_id=args.agent,
                desired_state=args.command,
            )
            db.commit()
            print(
                f"agent={args.agent} "
                f"desired_state={args.command}"
            )
            return

        if args.command == "pause-all":
            set_tenant_paused(
                db,
                tenant_id=args.tenant,
                paused=True,
            )
            db.commit()
            print(
                f"tenant={args.tenant} paused=true"
            )
            return

        if args.command == "resume-all":
            set_tenant_paused(
                db,
                tenant_id=args.tenant,
                paused=False,
            )
            db.commit()
            print(
                f"tenant={args.tenant} paused=false"
            )


if __name__ == "__main__":
    main()
