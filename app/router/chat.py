from fastapi import APIRouter, Depends, HTTPException
from app.schema.chat.conversation import CreateConversation
from app.dependencies import DBSession
from app.core.security.auth import oauth2_scheme
from app.services.user import user_service
from app.models.chat.conversations import Conversation,ConversationType
from app.models.chat.participants import ConversationParticipant,ParticipantRole
from app.models.chat.messages import Message,MessageType
from app.models.auth.user import User, UserRole
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
        conversation_id = conversation.id,
        user_id=token_user.id,
        role = ParticipantRole.OWNER
    )
    db.add(creator)

    db.add(
        Message(
            conversation_id=conversation.id,
            sender_id=token_user.id,
            type=MessageType.SYSTEM,
            message=f"{token_user.username} created the group"
        )
    )
    for user_id in form_data.participants:
        if user_id == token_user.id:
            continue

        user_exist = await db.get(User,user_id)

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
                conversation_id = conversation.id,
                sender_id=0,
                type=MessageType.SYSTEM,
                message=f"{user_exist.username} joined group"

            ))
    
    await db.commit()
    
    return {
        "message":"Group created",
        "conversation_id":conversation.id
    }

@router.post('/join-group')
async def join_group(group_id:str,db:DBSession,token:str = Depends(oauth2_scheme)):
    token_user = await user_service.get_current_user(db, token)
    
    conversation_res = await db.execute(select(Conversation).where(Conversation.id == group_id))
    conversation = conversation_res.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404,detail="Group not found")

    if conversation.type != ConversationType.GROUP:
        raise HTTPException(status_code=403,detail="Cannot join conversation (Not a Group)")
    
    existing_mem_res = await db.execute(
        select(Conversation)
        .join(ConversationParticipant)
        .where(
            ConversationParticipant.user_id == token_user.id,
            Conversation.id == group_id
        ))
    existing_member = existing_mem_res.scalar_one_or_none()
    if existing_member:
        raise HTTPException(status_code=401,detail="Already a member of group")

    db.add(
        ConversationParticipant(
            conversation_id=group_id,
            user_id = token_user.id,
            role = ParticipantRole.MEMBER,
        )
    )
    db.add(
        Message(
            conversation_id=group_id,
            sender_id=token_user.id,
            type = MessageType.SYSTEM,
            message=f"{token_user.username} joined group"
        )
    )
    await db.commit()
    return {
        "message":f"Joined in group {group_id}",
        "group":conversation
        }

@router.post('/leave-group')
async def leave_group(group_id:str,db:DBSession,token:str = Depends(oauth2_scheme)):
    token_user = await user_service.get_current_user(db, token)
    conversation_res = await db.execute(select(Conversation).where(Conversation.id == group_id))
    conversation = conversation_res.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404,detail="Group not found")

    if conversation.type != ConversationType.GROUP:
        raise HTTPException(status_code=403,detail="Cannot leave conversation (Not a Group)")

    existing_mem_res = await db.execute(
        select(ConversationParticipant)
        .where(
            ConversationParticipant.user_id == token_user.id,
            ConversationParticipant.conversation_id == group_id
        ))
    existing_member = existing_mem_res.scalar_one_or_none()
    if not existing_member:
        raise HTTPException(status_code=403,detail="Not a member of group")

    await db.delete(existing_member)
    db.add(
        Message(
            conversation_id=group_id,
            sender_id=token_user.id,
            type=MessageType.SYSTEM,
            message=f"{token_user.username} left group"
    ))
    await db.commit()
    return {
        "message": "Left group"
    }

from sqlalchemy.orm import joinedload

@router.post("/remove-member")
async def remove_member(
    target_id: UUID,
    group_id: UUID,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    token_user = await user_service.get_current_user(db, token)

    # Check the caller's role, not the target's role
    par_res = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == group_id,
            ConversationParticipant.user_id == token_user.id,
        )
    )
    participant = par_res.scalar_one_or_none()

    if not participant:
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    if participant.role not in [ParticipantRole.ADMIN, ParticipantRole.OWNER]:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to perform this action",
        )

    # Get the target participant and their user
    tar_par_res = await db.execute(
        select(ConversationParticipant)
        .options(joinedload(ConversationParticipant.user))
        .where(
            ConversationParticipant.conversation_id == group_id,
            ConversationParticipant.user_id == target_id,
        )
    )
    target_participant = tar_par_res.scalar_one_or_none()

    if not target_participant:
        raise HTTPException(status_code=404, detail="Member not in group")

    # Optional: don't allow removing the owner
    if target_participant.role == ParticipantRole.OWNER:
        raise HTTPException(
            status_code=403,
            detail="Cannot remove the group owner",
        )

    await db.delete(target_participant)

    db.add(
        Message(
            conversation_id=group_id,
            sender_id=token_user.id,
            type=MessageType.SYSTEM,
            message=f"{token_user.username} removed {target_participant.user.username}",
        )
    )

    await db.commit()

    return {
        "message": f"{token_user.username} removed {target_participant.user.username}"
    }
    

@router.post('create-dm')
async def create_dm(db:DBSession,target_id:str,token:str=Depends(oauth2_scheme)):
    token_user = await user_service.get_current_user(db,token)
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
    if conversation:
        return {"message":"DM already exists", "dm_id":conversation.id}

    dm = Conversation(
                type=ConversationType.PERSONAL,
            )
    db.add(dm)
    await db.flush()
    db.add(
        ConversationParticipant(
            conversation_id=dm.id,
            user_id=token_user.id,
            role=ParticipantRole.MEMBER
        )
    )

    db.add(
        ConversationParticipant(
            conversation_id=dm.id,
            user_id=target_id,
            role=ParticipantRole.MEMBER
        )
    )

    await db.commit()

    return {
        "message": "DM created",
        "conversation_id": dm.id
    }


@router.get('/get-all-groups')
async def get_all_groups(db:DBSession):
    results = await db.execute(select(Conversation).where(Conversation.type == ConversationType.GROUP))
    conversations = results.scalars().all()
    return conversations

@router.get('/get-group-members')
async def get_group_members(group_id:str, db:DBSession):
    mem_res = await db.execute(
        select(ConversationParticipant).
        where(ConversationParticipant.conversation_id == group_id)
    )
    members = mem_res.scalars().all()
    return members

@router.get('/get-all-dms')
async def get_all_dms(db:DBSession):
    results = await db.execute(select(Conversation).where(Conversation.type == ConversationType.PERSONAL))
    conversations = results.scalars().all()
    return conversations