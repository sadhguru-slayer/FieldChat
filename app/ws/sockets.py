import json
from uuid import UUID
from fastapi import APIRouter, WebSocket, Query, WebSocketDisconnect
from sqlalchemy import select

from app.database import SessionLocal
from app.services.user import user_service
from app.services.messages import MessageService
from app.ws.manager import manager
from app.services.cache_management.conversation import conversation_cache
from app.services.cache_management.presence import presence_cache
from app.services.cache_management.active_users import active_users_cache
from app.redis_client import r
from app.models.chat.messages import Message, MessageEvent
from app.models.chat.conversations import Conversation, ConversationType
from app.models.chat.participants import ConversationParticipant

router = APIRouter()

async def get_other_user(conversation_id, user_id, db):
    try:
        stmt = select(ConversationParticipant.user_id).where(
            ConversationParticipant.conversation_id == UUID(str(conversation_id)),
            ConversationParticipant.user_id != UUID(str(user_id)),
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
    except Exception as e:
        print(f"Error in get_other_user: {e}")
        return None

@router.websocket("/ws")
async def web_socket_endpoint(
    ws: WebSocket,
    token: str = Query(...),
):

    async with SessionLocal() as db:
        user = await user_service.get_current_user_ws(db, token)

    if not user:
        await ws.close(code=1008)
        return

    await manager.connect(str(user.id), user.username, ws)

    from app.redis.keys import RedisKeys
    conversation_ids = await conversation_cache.get_user_conversations(str(user.id))
    conn = manager._find_connection(str(user.id), ws)

    for conv_id in conversation_ids:
        await manager.join_conversation(
            conv_id, str(user.id), ws
        )
        # Watch DM participant presence to sync sidebar online/offline indicators
        conv_id_str = str(conv_id)
        members = await r.smembers(RedisKeys.conversation_members(conv_id_str))
        if len(members) == 2:
            for m in members:
                m_str = m.decode() if isinstance(m, bytes) else str(m)
                if m_str != str(user.id):
                    await presence_cache.watch(
                        watcher_id=str(user.id),
                        target_user_id=m_str,
                    )
                    if conn:
                        try:
                            conn.watched_users.add(UUID(m_str))
                        except Exception:
                            conn.watched_users.add(m_str)

    # Mark all messages sent to this user as delivered since they just came online
    async with SessionLocal() as db:
        service = MessageService(db)
        await service.mark_all_undelivered_as_delivered(user)

    try:
        while True:
            data = await ws.receive_json()
            #print("[WS RECV]", data, flush=True)
            event = data.get("event")
            conversation_id = data.get("conversation_id")
            message_id = data.get("message_id") or None
            content = data.get("content")
            reply_to_message_id = data.get("reply_to_message_id") or None
            media_url = data.get("media_url") or None
            media_name = data.get("media_name") or None

            if event in [
                MessageEvent.MESSAGE_CREATED.value,
                MessageEvent.MESSAGE_EDITED.value,
                MessageEvent.MESSAGE_DELETED_FOR_EVERYONE.value,
                MessageEvent.MESSAGE_DELETED_FOR_ME.value,
            ]:
                async with SessionLocal() as db:
                    service = MessageService(db)
                    if event == MessageEvent.MESSAGE_CREATED.value:
                        await service.create_message(user, conversation_id, content, reply_to_message_id, media_url, media_name)
                    elif event == MessageEvent.MESSAGE_EDITED.value:
                        await service.edit_message(user, conversation_id, message_id, content)
                    elif event == MessageEvent.MESSAGE_DELETED_FOR_EVERYONE.value:
                        await service.message_deleted_for_everyone(user, conversation_id, message_id)
                    elif event == MessageEvent.MESSAGE_DELETED_FOR_ME.value:
                        await service.message_delete_for_me(user, conversation_id, message_id)
            elif event == MessageEvent.MESSAGE_DELIVERED.value:
                async with SessionLocal() as db:
                    service = MessageService(db)
                    await service.mark_delivered(
                        user=user,
                        conversation_id=conversation_id,
                        message_id=message_id,
                    )

            elif event == MessageEvent.MESSAGE_READ.value:
                async with SessionLocal() as db:
                    service = MessageService(db)
                    await service.mark_read(
                        user=user,
                        conversation_id=conversation_id,
                        message_id=message_id,
                    )

            elif event == MessageEvent.MESSAGE_REACTION_ADDED.value:
                async with SessionLocal() as db:
                    service = MessageService(db)
                    await service.add_reaction(
                        user=user,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        reaction=content,
                    )

            elif event == MessageEvent.MESSAGE_REACTION_REMOVED.value:
                async with SessionLocal() as db:
                    service = MessageService(db)
                    await service.remove_reaction(
                        user=user,
                        conversation_id=conversation_id,
                        message_id=message_id,
                    )

            elif event == "typing":
                conversation_id = data.get("conversation_id")
                if not conversation_id:
                    continue

                if not await conversation_cache.is_member(
                    str(conversation_id),
                    str(user.id),
                ):
                    continue

                typing_payload = {
                    "event": "typing",
                    "conversation_id": str(conversation_id),
                    "sender_id": str(user.id),
                    "username": user.username,
                }

                await r.publish(
                    f"conversation:{str(conversation_id)}",
                    json.dumps(typing_payload),
                )

            elif event == "conversation.joined":
                conversation_id = data.get("conversation_id")
                #print("[WS JOIN]", conversation_id, "------------", flush=True)
                if not conversation_id:
                    continue

                conn = manager._find_connection(str(user.id), ws)
                if conn:
                    if conn.active_conv_id and conn.active_conv_id != conversation_id:
                        await active_users_cache.remove_active_user(conn.active_conv_id, str(user.id))
                    conn.active_conv_id = conversation_id
                    await active_users_cache.add_active_user(conversation_id, str(user.id))

                await manager.join_conversation(
                    conversation_id,
                    str(user.id),
                    ws,
                )

                async with SessionLocal() as db:
                    conversation = await db.get(Conversation, UUID(str(conversation_id)))
                    if conversation and conversation.type == ConversationType.PERSONAL:
                        other_user_id = await get_other_user(
                            conversation_id,
                            user.id,
                            db,
                        )

                        if other_user_id:
                            if conn:
                                conn.watched_users.add(other_user_id)

                            await presence_cache.watch(
                                watcher_id=str(user.id),
                                target_user_id=str(other_user_id),
                            )
                            online = await presence_cache.online(str(other_user_id))

                            last_seen = None
                            if not online:
                                last_seen = await presence_cache.get_last_seen(str(other_user_id))

                            await ws.send_json({
                                "event": "presence",
                                "user_id": str(other_user_id),
                                "online": bool(online),
                                "last_seen": last_seen,
                            })
            elif event == "conversation.left":
                conversation_id = data.get("conversation_id")
                if not conversation_id:
                    continue

                conn = manager._find_connection(str(user.id), ws)
                if conn and conn.active_conv_id == conversation_id:
                    conn.active_conv_id = None
                    await active_users_cache.remove_active_user(conversation_id, str(user.id))

                async with SessionLocal() as db:
                    conversation = await db.get(Conversation, UUID(str(conversation_id)))
                    if conversation and conversation.type == ConversationType.PERSONAL:
                        other_user_id = await get_other_user(
                            conversation_id,
                            user.id,
                            db,
                        )

                        if other_user_id:
                            conn = manager._find_connection(str(user.id), ws)
                            if conn:
                                conn.watched_users.discard(other_user_id)

                            await presence_cache.unwatch(
                                watcher_id=str(user.id),
                                target_user_id=str(other_user_id),
                            )
            elif event == "presence.unfocus":
                import time
                await presence_cache.set_offline(str(user.id))
                await r.publish(
                    "presence",
                    json.dumps({
                        "event": "presence",
                        "user_id": str(user.id),
                        "online": False,
                        "last_seen": int(time.time()),
                    })
                )
            elif event == "presence.focus":
                await r.sadd("online_users", str(user.id))
                await r.publish(
                    "presence",
                    json.dumps({
                        "event": "presence",
                        "user_id": str(user.id),
                        "online": True,
                    })
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS Error] Exception in websocket loop: {e}")
    finally:
        await manager.disconnect(
            str(user.id),
            ws,
        )