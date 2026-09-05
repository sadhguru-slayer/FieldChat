from redis.exceptions import ResponseError

from app.redis_client import r
from app.redis.keys import RedisKeys
import json

MESSAGE_EVENT_STREAM = RedisKeys.message_event_stream()


async def ensure_message_event_group(
    instance_id: str,
) -> str:
    """
    Creates an instance-specific Redis Stream consumer group.

    Each application instance gets its own group, allowing every
    running instance to receive every message event.
    """

    group_name = f"message-events:{instance_id}"

    try:
        await r.xgroup_create(
            name=MESSAGE_EVENT_STREAM,
            groupname=group_name,
            id="0",
            mkstream=True,
        )

        print(
            f"[Startup] Redis stream group created: "
            f"stream={MESSAGE_EVENT_STREAM}, "
            f"group={group_name}"
        )

    except ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            print(
                f"[Startup] Redis stream group already exists: "
                f"group={group_name}"
            )
        else:
            raise

    return group_name


async def add_to_stream(
    *,
    channel: str,
    event_id: str,
    event_type: str,
    payload: dict,
) -> str:
    """
    Add an outbox event to a Redis Stream.

    Returns the Redis Stream message ID.
    """

    stream_id = await r.xadd(
        channel,
        {
            "event_id": event_id,
            "event_type": event_type,
            "payload": json.dumps(
                payload,
                separators=(",", ":"),
            ),
        },
    )

    return stream_id