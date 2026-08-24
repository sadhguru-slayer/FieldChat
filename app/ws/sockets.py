from fastapi import APIRouter, WebSocket, Query, WebSocketDisconnect
from app.database import SessionLocal
from app.services.user import user_service
from app.services.messages import MessageService
from app.ws.manager import manager
from app.services.cache_management.conversation import conversation_cache
from app.models.chat.messages import Message, MessageEvent
router = APIRouter()

@router.websocket("/ws")
async def web_socket_endpoint(
    ws: WebSocket,
    # token : str = Query(...),
    user_id:str
    ):

    async with SessionLocal() as db:
        # user = await user_service.get_current_user_ws(db, token)
        user = await user_service.get_user_with_id_ws(db, user_id)

    if not user:
        await ws.close(code = 1000)
        return

    await manager.connect(str(user.id), user.username, ws)

    conversation_ids = await conversation_cache.get_user_conversations(str(user.id))

    for conv_id in conversation_ids:
        await manager.join_conversation(
            conv_id,str(user.id),ws
        )
    try:
        while True:
            data = await ws.receive_json()
            print(data)
            event = data.get("event")
            conversation_id=data.get("conversation_id")
            message_id = data.get("message_id") or None
            content = data.get("content")

            if event in [
                MessageEvent.MESSAGE_CREATED.value,
                MessageEvent.MESSAGE_EDITED.value,
                MessageEvent.MESSAGE_DELETED_FOR_EVERYONE.value,
                MessageEvent.MESSAGE_DELETED_FOR_ME.value
                ]:
                async with SessionLocal() as db:
                    service = MessageService(db)
                    if event == MessageEvent.MESSAGE_CREATED.value:
                        await service.create_message(user,conversation_id,content)
                    elif event == MessageEvent.MESSAGE_EDITED.value:
                        await service.edit_message(user,conversation_id,message_id,content)
                    elif event == MessageEvent.MESSAGE_DELETED_FOR_EVERYONE.value:
                        await service.message_deleted_for_everyone(user,conversation_id,message_id)
                    elif event == MessageEvent.MESSAGE_DELETED_FOR_ME.value:
                        await service.message_delete_for_me(user,conversation_id,message_id)
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

                conversation_id = data.get(
                    "conversation_id"
                )

                if not conversation_id:
                    continue

                if not await conversation_cache.is_member(
                    conversation_id,
                    user.id
                ):
                    continue

                typing_payload = {
                    "event": "typing",
                    "conversation_id": conversation_id,
                    "sender_id": user.id,
                    "username": user.username
                }

                await r.publish(
                    f"conversation:{conversation_id}",
                    json.dumps(typing_payload)
                )
            
            elif event == "conversation.joined":

                conversation_id = data["conversation_id"]
                if not conversation_id:
                    continue

                # 1. register locally (Phase 3 addition)
                await manager.join_conversation(
                    conversation_id,
                    user.id,
                    ws
                )
                
                async with SessionLocal() as db:
                    conversation = await db.get(Conversation, conversation_id)
                    if conversation and conversation.type == ConversationType.PERSONAL:
                        other_user_id = await get_other_user(
                            conversation_id,
                            user.id,
                            db
                        )

                        if other_user_id:
                            conn = manager._find_connection(user.id, ws)
                            if conn:
                                conn.watched_users.add(other_user_id)
                                
                            await PresenceCache.watch(
                                watcher_id=user.id,
                                target_id=other_user_id
                            )
                        online = await PresenceCache.online(other_user_id)

                        await ws.send_json({
                            "event": "presence",
                            "user_id": other_user_id,
                            "online": bool(online)
                        })
            elif event == "conversation.left":

                conversation_id = data["conversation_id"]
                if not conversation_id:
                    continue

                # await manager.leave_conversation(
                #     conversation_id,
                #     user.id,
                #     ws
                # )

                async with SessionLocal() as db:
                    conversation = await db.get(Conversation, conversation_id)
                    if conversation and conversation.type == ConversationType.PERSONAL:
                        other_user_id = await get_other_user(
                            conversation_id,
                            user.id,
                            db
                        )
                    
                        if other_user_id:
                            conn = manager._find_connection(user.id, ws)
                            if conn:
                                conn.watched_users.discard(other_user_id)
                                
                            await PresenceCache.unwatch(
                                watcher_id=user.id,
                                target_id=other_user_id
                            )
            
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(
            user.id,
            ws
        )