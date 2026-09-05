# app/services/outbox_service.py

import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models.chat.outbox import OutboxEvent
from app.redis_client import r


async def outbox_worker():
    print("[Outbox] Worker started")

    while True:
        try:
            processed = await process_outbox()

            if processed == 0:
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0.05)

        except asyncio.CancelledError:
            print("[Outbox] Worker shutting down")
            raise

        except Exception as exc:
            print(f"[Outbox] Worker error: {exc}")

            # Print the actual traceback while debugging
            import traceback
            traceback.print_exc()

            await asyncio.sleep(2)


async def process_outbox():
    # print("[Outbox] Checking for pending events...")

    async with SessionLocal() as db:

        stmt = (
            select(OutboxEvent)
            .where(
                OutboxEvent.processed_at.is_(None)
            )
            .order_by(OutboxEvent.created_at)
            .limit(100)
            .with_for_update(skip_locked=True)
        )

        result = await db.execute(stmt)

        events = result.scalars().all()

        # print(f"[Outbox] Found {len(events)} pending event(s)")

        if not events:
            return 0

        async with r.pipeline(transaction=False) as pipe:

            for event in events:

                # print(
                #     f"[Outbox] Publishing "
                #     f"id={event.id} "
                #     f"type={event.event_type} "
                #     f"channel={event.channel}"
                # )

                # print(
                #     f"[Outbox] Payload: "
                #     f"{event.payload}"
                # )

                # Count this as a publishing attempt
                event.attempts += 1

                pipe.xadd(
                    event.channel,
                    {
                        "event_id": str(event.id),
                        "event_type": event.event_type,
                        "payload": json.dumps(
                            event.payload,
                            separators=(",", ":"),
                        ),
                    },
                )

            await pipe.execute()

        # print(
        #     f"[Outbox] Successfully published "
        #     f"{len(events)} event(s)"
        # )

        now = datetime.now(timezone.utc)

        for event in events:
            event.processed_at = now

        await db.commit()

        # print(
        #     f"[Outbox] Marked "
        #     f"{len(events)} event(s) as processed"
        # )

        return len(events)


def add_outbox_event(
    db,
    *,
    event_type: str,
    channel: str,
    payload: dict,
):
    event = OutboxEvent(
        event_type=event_type,
        channel=channel,
        payload=payload,
        attempts=0,
    )

    db.add(event)

    print(
        f"[Outbox] Added event "
        f"type={event_type} "
        f"channel={channel} "
        f"message={payload.get('message')}"
    )

    return event