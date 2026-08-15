from fastapi import APIRouter, Depends, HTTPException
from app.schema.chat.conversation import CreateConversation
from app.dependencies import DBSession
from app.core.security.auth import oauth2_scheme
from app.services.user import user_service
from app.models.chat.conversations import Conversation,ConversationType
from app.models.chat.participants import ConversationParticipant,ParticipantRole
from app.models.chat.messages import Message,MessageType,MessageDeleteState,MessageReceipt, MessageEvent
from app.models.auth.user import User, UserRole
from sqlalchemy import select,func,outerjoin,and_
from datetime import timezone

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


@router.get('/get-messages')
async def get_messages(conversation_id:str,db:DBSession,token:str=Depends(oauth2_scheme)):
    token_user = await user_service.get_current_user(db,token)
    stmt_conv = select(Conversation).where(
        Conversation.id == conversation_id
    )

    conv_result = await db.execute(stmt_conv)
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    result = await db.execute(
        select(
        Message,
        User.username,
        MessageDeleteState.user_id.label("is_deleted_for_me"),
        MessageReceipt
        )
        .outerjoin(User, User.id==Message.sender_id)
        .outerjoin(
            MessageDeleteState,
            and_(
                MessageDeleteState.message_id == Message.id,
                MessageDeleteState.user_id == token_user.id
            )
        )
        .outerjoin(
            MessageReceipt,
            and_(
                MessageReceipt.message_id == Message.id,
                MessageReceipt.user_id == token_user.id
            )
        )
        .where(Message.conversation_id == UUID(conversation_id))
        .order_by(Message.timestamp.asc())
        .limit(150)
        )
    
    rows = result.all()
    events = []
    for message, username, is_deleted_for_me, message_receipt in rows:
        if is_deleted_for_me:
            events.append({
                "event":MessageEvent.MESSAGE_DELETED_FOR_ME,
                "data":{
                    "message_id":message.id
                }
            })
            continue
        if message.is_deleted_global:
            events.append(
                {
                    "event":MessageEvent.MESSAGE_DELETED_FOR_EVERYONE,
                    "data":{
                        "message_id":message.id,
                        "sender_id":message.sender_id if message.type != MessageType.SYSTEM else "SYSTEM",
                        "username": username if username and message.type != MessageType.SYSTEM else "SYSTEM",
                        "message": "Deleted for everyone",
                        "timestamp": (
                            message.timestamp.astimezone(timezone.utc).isoformat()
                            if message.timestamp else None
                        ),
                        "type": message.type.value
                    }
                }
            )
            continue
        is_mine = message.sender_id == token_user.id
        delivered = (
            message_receipt is not None
            and message_receipt.delivered_at is not None
        )

        read = (
            message_receipt is not None
            and message_receipt.read_at is not None
        )
        if message.edited_at and message.edited_at > message.timestamp:
            events.append(
                {
                    "event":MessageEvent.MESSAGE_EDITED,
                    "data": {
                        "message_id": message.id,
                        "sender_id":message.sender_id if message.type != MessageType.SYSTEM else "SYSTEM",
                        "username": username if username and message.type != MessageType.SYSTEM else "SYSTEM",
                        "message": message.message,
                        "timestamp": message.timestamp.astimezone(timezone.utc).isoformat(),
                        "edited_at": message.edited_at.astimezone(timezone.utc).isoformat(),
                        "type": message.type.value,
                        "delivered": delivered if is_mine else None,
                        "read": read if is_mine else None,
                    }
                }
            )
            continue
        events.append(
            {
            "event": "message",
            "data": {
            "message_id": message.id,
            "sender_id":message.sender_id if message.type != MessageType.SYSTEM else "SYSTEM",
            "username": username if username and message.type != MessageType.SYSTEM else "SYSTEM",
            "message": message.message,
            "timestamp": (
                message.timestamp.astimezone(timezone.utc).isoformat()
                if message.timestamp else None
            ),
            "edited_at": message.edited_at.astimezone(timezone.utc).isoformat() if message.edited_at else None,
            "type": message.type.value,
            "delivered": delivered if is_mine else None,
            "read": read if is_mine else None,
        }
        }
        )
        
    return events


