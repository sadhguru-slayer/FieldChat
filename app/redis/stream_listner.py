import asyncio
import json
import uuid

from app.redis_client import r
from app.redis.redis_groups import MESSAGE_EVENT_STREAM
from app.redis.handlers import message_send_handler


async def start_redis_stream_listener(
    group_name: str,
):
    """
    Listen to Redis Stream events using an instance-specific
    consumer group.

    Every application instance has its own group, so every
    instance receives every event.
    """

    consumer_name = f"consumer:{uuid.uuid4().hex}"

    # print(
    #     f"[Redis Stream] Starting listener "
    #     f"stream={MESSAGE_EVENT_STREAM}, "
    #     f"group={group_name}, "
    #     f"consumer={consumer_name}"
    # )

    while True:
        try:
            messages = await r.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams={
                    MESSAGE_EVENT_STREAM: ">",
                },
                count=100,
                block=5000,
            )
            if not messages:
                continue

            for stream_name, stream_messages in messages:
                for message_id, fields in stream_messages:
                    try:
                        await handle_stream_message(
                            message_id=message_id,
                            fields=fields,
                        )

                        # Acknowledge only after successful processing.
                        await r.xack(
                            stream_name,
                            group_name,
                            message_id,
                        )

                    except Exception as exc:
                        print(
                            f"[Redis Stream] Failed to process "
                            f"message={message_id}: {exc}"
                        )

                        # DO NOT XACK here.
                        #
                        # The message remains pending and can later
                        # be recovered with XAUTOCLAIM.

        except asyncio.CancelledError:
            print(
                f"[Redis Stream] Listener shutting down "
                f"group={group_name}"
            )
            raise

        except Exception as exc:
            print(
                f"[Redis Stream] Listener error: {exc}"
            )

            # Prevent a tight reconnect loop if Redis goes down.
            await asyncio.sleep(2)


async def handle_stream_message(
    *,
    message_id,
    fields: dict,
):
    """
    Process one Redis Stream message.
    """

    # redis-py may return bytes depending on configuration.
    if isinstance(message_id, bytes):
        message_id = message_id.decode()

    event_id = fields.get("event_id")
    event_type = fields.get("event_type")
    payload = fields.get("payload")

    if isinstance(event_id, bytes):
        event_id = event_id.decode()

    if isinstance(event_type, bytes):
        event_type = event_type.decode()

    if isinstance(payload, bytes):
        payload = payload.decode()

    if isinstance(payload, str):
        payload = json.loads(payload)

    if not isinstance(payload, dict):
        raise ValueError(
            f"Invalid payload for stream message "
            f"{message_id}"
        )

    conversation_id = payload.get("conversation_id")

    if not conversation_id:
        raise ValueError(
            f"Stream message {message_id} "
            "has no conversation_id"
        )

    # print(
    #     f"[Redis Stream] Received "
    #     f"redis_id={message_id}, "
    #     f"event_id={event_id}, "
    #     f"event_type={event_type}"
    # )

    await message_send_handler(
        conversation_id=str(conversation_id),
        data=payload,
    )
 