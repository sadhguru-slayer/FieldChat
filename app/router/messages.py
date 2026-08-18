from fastapi import APIRouter, Depends, HTTPException
from app.schema.chat.conversation import CreateConversation
from app.dependencies import DBSession
from app.core.security.auth import oauth2_scheme
from app.services.user import user_service
from app.models.chat.conversations import Conversation,ConversationType
from app.models.chat.participants import ConversationParticipant,ParticipantRole
from app.models.chat.messages import Message,MessageType,MessageDeleteState,MessageReceipt, MessageEvent
from app.models.auth.user import User, UserRole
from sqlalchemy import select,func,outerjoin,and_,exists
from sqlalchemy.orm import selectinload
from datetime import timezone
from app.services.messages import MessageService


from uuid import UUID

general_message_router = APIRouter(
    prefix = "/api/dev/messages",
    tags = ["General Message Router Manager"]
)

router = APIRouter(
    prefix="/api/messages",
    tags = ["Message Router"]
)

@general_message_router.get("/get-all-messages")
async def get_all_messages(db: DBSession):
    result = await db.scalars(select(Message))
    messages = result.all()
    return messages


@router.get("/get-messages")
async def get_messages(
    conversation_id: str,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    token_user = await user_service.get_current_user(db, token)

    try:
        conversation_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    conversation = (
        await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_uuid
            )
        )
    ).scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(
            Message,
            User.username,
            MessageDeleteState.user_id.label("is_deleted_for_me"),
            exists(
                select(1).where(
                    and_(
                        MessageReceipt.message_id == Message.id,
                        MessageReceipt.user_id != token_user.id,
                        MessageReceipt.delivered_at.is_not(None),
                    )
                )
            ).label("is_delivered"),
            exists(
                select(1).where(
                    and_(
                        MessageReceipt.message_id == Message.id,
                        MessageReceipt.user_id != token_user.id,
                        MessageReceipt.read_at.is_not(None),
                    )
                )
            ).label("is_read"),
        )
        .outerjoin(User, User.id == Message.sender_id)
        .outerjoin(
            MessageDeleteState,
            and_(
                MessageDeleteState.message_id == Message.id,
                MessageDeleteState.user_id == token_user.id,
            ),
        )
        .options(
            selectinload(Message.reactions),
            selectinload(Message.reply_to).selectinload(Message.sender),
            selectinload(Message.reply_to).selectinload(Message.delete_states),
        )
        .where(Message.conversation_id == conversation_uuid)
        .order_by(Message.timestamp.asc())
        .limit(150)
    )

    rows = result.all()
    events = []

    for message, username, is_deleted_for_me, delivered, read in rows:
        if conversation.type == ConversationType.GROUP:
            read = False

        if is_deleted_for_me:
            events.append({
                "event": MessageEvent.MESSAGE_DELETED_FOR_ME,
                "data": {"message_id": str(message.id)},
            })
            continue

        if message.is_deleted_global:
            events.append({
                "event": MessageEvent.MESSAGE_DELETED_FOR_EVERYONE,
                "data": {
                    "message_id": str(message.id),
                    "sender_id": (
                        str(message.sender_id)
                        if message.type != MessageType.SYSTEM
                        else "SYSTEM"
                    ),
                    "username": (
                        username
                        if username and message.type != MessageType.SYSTEM
                        else "SYSTEM"
                    ),
                    "message": "Deleted for everyone",
                    "timestamp": (
                        message.timestamp.astimezone(timezone.utc).isoformat()
                        if message.timestamp
                        else None
                    ),
                    "type": message.type.value,
                },
            })
            continue

        is_mine = message.sender_id == token_user.id

        reply_to = None
        if message.reply_to:
            reply = message.reply_to
            reply_deleted_for_me = any(
                state.user_id == token_user.id
                for state in reply.delete_states
            )

            if reply_deleted_for_me or reply.is_deleted_global:
                reply_to = {
                    "message_id": str(reply.id),
                    "is_deleted": True,
                    "message": "Deleted for everyone"
                    if reply.is_deleted_global
                    else "Message unavailable",
                }
            else:
                reply_to = {
                    "message_id": str(reply.id),
                    "sender_id": (
                        str(reply.sender_id)
                        if reply.type != MessageType.SYSTEM
                        else "SYSTEM"
                    ),
                    "username": (
                        reply.sender.username
                        if reply.sender and reply.type != MessageType.SYSTEM
                        else "SYSTEM"
                    ),
                    "message": reply.message,
                    "timestamp": (
                        reply.timestamp.astimezone(timezone.utc).isoformat()
                        if reply.timestamp
                        else None
                    ),
                    "type": reply.type.value,
                    "is_deleted": False,
                }

        reaction_map = {}
        for reaction in message.reactions:
            if reaction.reaction not in reaction_map:
                reaction_map[reaction.reaction] = {
                    "reaction": reaction.reaction,
                    "count": 0,
                    "reacted_by_me": False,
                }
            reaction_map[reaction.reaction]["count"] += 1
            if reaction.user_id == token_user.id:
                reaction_map[reaction.reaction]["reacted_by_me"] = True

        data = {
            "is_mine": is_mine,
            "message_id": str(message.id),
            "sender_id": (
                str(message.sender_id)
                if message.type != MessageType.SYSTEM
                else "SYSTEM"
            ),
            "username": (
                username
                if username and message.type != MessageType.SYSTEM
                else "SYSTEM"
            ),
            "message": message.message,
            "timestamp": (
                message.timestamp.astimezone(timezone.utc).isoformat()
                if message.timestamp
                else None
            ),
            "edited_at": (
                message.edited_at.astimezone(timezone.utc).isoformat()
                if message.edited_at
                else None
            ),
            "type": message.type.value,
            "delivered": delivered if is_mine else None,
            "read": read if is_mine else None,
            "reply_to": reply_to,
            "reactions": list(reaction_map.values()),
        }

        events.append({
            "event": (
                MessageEvent.MESSAGE_EDITED
                if message.edited_at and message.edited_at > message.timestamp
                else MessageEvent.MESSAGE_CREATED
            ),
            "data": data,
        })

    return events

@router.post("/create-message")
async def create_message(
    conversation_id: str,
    content: str,
    reply_to_message_id: str | None = None,
    db: DBSession = None,
    token: str = Depends(oauth2_scheme),
):
    message_service = MessageService(db)
    token_user = await user_service.get_current_user(db, token)
    try:
        conversation_uuid = UUID(conversation_id)
        reply_uuid = UUID(reply_to_message_id) if reply_to_message_id else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    conversation = await db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_uuid
        )
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    result = await message_service.create_message(
        user=token_user,
        conversation_id=conversation_uuid,
        content=content,
        reply_to_message_id=reply_uuid,
    )

    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.error,
        )

    return result.data


@router.patch('/edit-message')
async def edit_message(conversation_id:str,message_id:str,content:str, db:DBSession, token:str = Depends(oauth2_scheme)):
    message_service = MessageService(db)
    token_user = await user_service.get_current_user(db,token)
    conversation = await db.scalar(select(Conversation).where(Conversation.id == UUID(conversation_id)))
    if not conversation:
        raise HTTPException(status_code=404, detail = "Conversation not found")
    result = await message_service.edit_message(
        user = token_user,
        conversation_id = conversation_id,
        message_id = message_id,
        content = content
    )
    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.error,
        )

    return result.data

@router.delete("/delete-for-everyone")
async def delete_for_everyone(conversation_id:str,message_id:str,db:DBSession,token:str = Depends(oauth2_scheme)):
    message_service = MessageService(db)
    token_user = await user_service.get_current_user(db,token)
    conversation = await db.scalar(select(Conversation).where(Conversation.id == UUID(conversation_id)))
    if not conversation:
        raise HTTPException(status_code=404, detail = "Conversation not found")
    result = await message_service.message_deleted_for_everyone(
        user = token_user,
        conversation_id = conversation_id,
        message_id = message_id,
    )
    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.error,
        )

    return result.data

@router.delete("/delete-for-me")
async def delete_for_me(conversation_id:str,message_id:str,db:DBSession,token:str = Depends(oauth2_scheme)):
    message_service = MessageService(db)
    token_user = await user_service.get_current_user(db,token)
    conversation = await db.scalar(select(Conversation).where(Conversation.id == UUID(conversation_id)))
    if not conversation:
        raise HTTPException(status_code=404, detail = "Conversation not found")
    result = await message_service.message_delete_for_me(
        user = token_user,
        conversation_id = conversation_id,
        message_id = message_id,
    )
    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.error,
        )

    return result.data


@router.post("/messages/{message_id}/delivered")
async def mark_message_delivered(
    message_id: UUID,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    message_service = MessageService(db)
    token_user = await user_service.get_current_user(db,token,)
    result = await message_service.mark_delivered(
        user=token_user,
        message_id=message_id,
    )
    if not result.success:
        raise HTTPException(
            status_code = 400,
            detail=result.error,
        )

    return result.data

@router.post("/messages/{message_id}/read")
async def mark_message_read(
    message_id: UUID,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    message_service = MessageService(db)
    token_user = await user_service.get_current_user(db,token,)
    result = await message_service.mark_read(
        user=token_user,
        message_id=message_id,
    )
    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.error,
        )

    return result.data


@router.post("/react-to-message")
async def react_to_message(
    conversation_id: str,
    message_id: str,
    reaction: str,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    token_user = await user_service.get_current_user(db, token)

    try:
        conversation_uuid = UUID(conversation_id)
        message_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    result = await MessageService(db).add_reaction(
        user=token_user,
        conversation_id=conversation_uuid,
        message_id=message_uuid,
        reaction=reaction,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return result.data

@router.delete("/remove-reaction")
async def remove_reaction(
    conversation_id: str,
    message_id: str,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    token_user = await user_service.get_current_user(db, token)

    try:
        conversation_uuid = UUID(conversation_id)
        message_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    result = await MessageService(db).remove_reaction(
        user=token_user,
        conversation_id=conversation_uuid,
        message_id=message_uuid,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return result.data
