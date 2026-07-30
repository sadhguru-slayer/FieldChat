from fastapi import APIRouter, Depends, HTTPException
from app.schema.chat.conversation import CreateConversation
from app.dependencies import DBSession
from app.core.security.auth import oauth2_scheme
from app.services.user import user_service
from app.models.chat.conversations import Conversation,ConversationType
from app.models.chat.participants import ConversationParticipant,ParticipantRole
from app.models.chat.messages import Message,MessageType
from app.models.auth.user import User
from sqlalchemy import select

from uuid import UUID

router = APIRouter(
    prefix="/api/chat",
    tags = ["Chat Router Manager"]
)

@router.post("/create-coversation")
async def create_coversation(form_data:CreateConversation,db:DBSession,token:str = Depends(oauth2_scheme)):
    token_user = await user_service.get_current_user(db,token)
    conversation = Conversation(
        type=ConversationType.GROUP,
        name=form_data.conversation_name or None
    )
    db.add(conversation)
    await db.flush()
    
    creator = ConversationParticipant(
        conversation_id = UUID(conversation.id),
        user_id=token_user.id,
        role = ParticipantRole.OWNER
    )
    db.add(creator)

    db.add(
        Message(
            conversation_id=int(conversation.id),
            sender_id=token_user.id,
            type=MessageType.SYSTEM,
            message=f"{token_user.username} created the group"
        )
    )
    for user_id in form_data.participants:
        if user_id == token_user.id:
            continue

        user_exist = await db.get(User,UUID(user_id))

        if not user_exist:
            continue

        db.add(
            ConversationParticipant(
                conversation_id = conversation.id,
                user_id=user_id,
                role=ParticipantRole.MEMBER
            )
        )

        if conversation.type == ConversationType.GROUP:
            db.add(Message(
                conversation_id = int(conversation.id),
                sender_id=0,
                type=MessageType.SYSTEM,
                message=f"{user_exist.username} joined group"

            ))
    
    await db.commit()
    
    return {
        "message":"Group created",
        "conversation_id":conversation.id
    }

@router.get('create-dm')
async def create_dm(db:DBSession,target_id:str,token:str=Depends(oauth2_scheme)):
    token_user = user_service.get_current_user(db,token)
    if(target_id == token_user.id):
        raise HTTPException(status_code=401,detail="Cannot make a dm yourself")
    target_user = user_service.get_user_with_id(db,target_id)
    if not target_user:
        raise HTTPException(status_code=401,detail="Target user not found")
    existing_dm =await db.execute(
        select(Conversation)
        .join(ConversationParticipant,
              Conversation.id == ConversationParticipant.conversation_id
        )
        .where(
            Conversation.type == ConversationType.PERSONAL,
            ConversationParticipant.user_id.in_(
                [token_user.id, target_id]
            )
        )
    )
    conversation = existing_dm.scalar_one_or_none()
    if existing_dm:
        return {"message":"DM already exists", "dm_id":conversation.id}

    dm =   Conversation(
                type=ConversationType.PERSONAL,
            )
    db.add(dm)
    db.flush()
    db.add(
        ConversationParticipant(
            conversation_id=conversation.id,
            user_id=token_user.id,
            role=ParticipantRole.MEMBER
        )
    )

    db.add(
        ConversationParticipant(
            conversation_id=conversation.id,
            user_id=target_id,
            role=ParticipantRole.MEMBER
        )
    )

    await db.commit()

    return {
        "message": "DM created",
        "conversation_id": conversation.id
    }

