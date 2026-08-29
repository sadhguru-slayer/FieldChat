from fastapi import APIRouter, Depends, HTTPException
from app.schema.chat.conversation import CreateConversation, ConversationPatch
from app.dependencies import DBSession
from app.core.security.auth import oauth2_scheme
from app.services.user import user_service
from app.services.cache_management.conversation import conversation_cache
from app.services.notification_service import notification_service
from app.models.notification import NotificationType
from app.redis_client import r
from app.models.chat.conversations import Conversation,ConversationType
from app.models.chat.participants import ConversationParticipant,ParticipantRole
from app.models.chat.messages import Message,MessageType,MessageDeleteState,MessageReceipt,MessageEvent
from app.models.auth.user import User, UserRole
from sqlalchemy import or_, select, delete,func
from app.models.profile.profile import UserProfile
from app.redis.keys import RedisKeys
from app.schema.chat.message import MessageEventPayload


from uuid import UUID

async def broadcast_system_message(conversation_id, db_message: Message, sender_username: str):
    event_payload = MessageEventPayload(
        type="SYSTEM",
        event=MessageEvent.MESSAGE_CREATED,
        message_id=str(db_message.id),
        conversation_id=str(conversation_id),
        sender_id=str(db_message.sender_id) if db_message.sender_id else None,
        username=sender_username,
        message=db_message.message,
        timestamp=db_message.created_at.isoformat() if db_message.created_at else None,
    )
    await r.publish(
        RedisKeys.conversation_key(str(conversation_id)),
        event_payload.model_dump_json(),
    )

router = APIRouter(
    prefix="/api/chat",
    tags = ["Chat Router Manager"]
)

general_chat_router = APIRouter(
    prefix="/api/dev/chat",
    tags = ["General Chat Router Manager"]
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
                conversation_id=conversation.id,
                sender_id=token_user.id,
                type=MessageType.SYSTEM,
                message=f"{user_exist.username} joined group",
            ))
    
    await db.commit()
    await conversation_cache.sync_conversation(str(conversation.id), db)
    
    for p in form_data.participants:
        if str(p) != str(token_user.id):
            try:
                await notification_service.send_notification(
                    db=db,
                    user_id=UUID(str(p)),
                    title="Added to Group",
                    body=f"{token_user.username} added you to '{conversation.name or 'Group'}'",
                    type=NotificationType.SYSTEM,
                    data={
                        "conversation_id": str(conversation.id),
                        "sub_event": "conversation.added",
                        "username": token_user.username,
                        "group_name": conversation.name or "Group",
                    }
                )
            except Exception as e:
                print(f"Failed to send group notification: {e}")
    
    return {
        "message":"Group created",
        "conversation_id":conversation.id
    }

@router.patch("/conversation/{conversation_id}")
async def patch_conversation(
    conversation_id: str,
    data: ConversationPatch,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    token_user = await user_service.get_current_user(db, token)

    conversation = await db.get(
        Conversation,
        UUID(conversation_id)
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    if conversation.is_deleted:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    # These properties only make sense for groups
    if conversation.type != ConversationType.GROUP:
        if data.model_fields_set:
            raise HTTPException(
                status_code=400,
                detail="Name, description and avatar are only allowed for group conversations"
            )

    # TODO: replace with your existing participant/admin check
    participant = await db.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.user_id == token_user.id,
        )
    )

    if not participant:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this conversation"
        )

    if "name" in data.model_fields_set:
        conversation.name = data.name

    if "description" in data.model_fields_set:
        conversation.description = data.description

    if "avatar_url" in data.model_fields_set:
        conversation.avatar_url = data.avatar_url

    await db.commit()
    await db.refresh(conversation)

    return {
        "conversation_id": conversation.id,
        "type": conversation.type.value,
        "name": conversation.name,
        "description": conversation.description,
        "avatar_url": conversation.avatar_url,
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
    await conversation_cache.add_member(
        group_id,str(token_user.id)
    )
    return {
        "message":f"Joined in group {group_id}",
        "group":conversation
        }


@router.post("/add-member")
async def add_member(
    group_id: str,
    target_ids: list[str],
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    token_user = await user_service.get_current_user(db, token)

    try:
        group_uuid = UUID(group_id)
        user_ids = list({UUID(uid) for uid in target_ids})  # remove duplicates
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="One or more IDs are invalid UUIDs.",
        )

    if not user_ids:
        return {"message": "No users to add."}

    # Check group exists
    conversation = await db.scalar(
        select(Conversation).where(
            Conversation.id == group_uuid
        )
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Group not found.",
        )

    # Check requester permissions
    participant = await db.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == group_uuid,
            ConversationParticipant.user_id == token_user.id,
        )
    )

    if not participant:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group.",
        )

    if participant.role not in (
        ParticipantRole.ADMIN,
        ParticipantRole.OWNER,
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to perform this action.",
        )

    # Fetch all requested users
    users = (
        await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
    ).scalars().all()

    users_map = {user.id: user for user in users}

    # Fetch existing members
    existing_members = set(
        (
            await db.execute(
                select(ConversationParticipant.user_id).where(
                    ConversationParticipant.conversation_id == group_uuid,
                    ConversationParticipant.user_id.in_(user_ids),
                )
            )
        ).scalars().all()
    )

    errors = {
        "missing_users": [],
        "existing_members": [],
    }

    new_participants = []
    system_messages = []

    for user_id in user_ids:

        # User doesn't exist
        if user_id not in users_map:
            errors["missing_users"].append(str(user_id))
            continue

        # Already in group
        if user_id in existing_members:
            errors["existing_members"].append(str(user_id))
            continue

        new_participants.append(
            ConversationParticipant(
                conversation_id=group_uuid,
                user_id=user_id,
            )
        )

        system_messages.append(
            Message(
                conversation_id=group_uuid,
                sender_id=token_user.id,
                type=MessageType.SYSTEM,
                message=f"{token_user.username} added {users_map[user_id].username}",
            )
        )

    if new_participants:
        db.add_all(new_participants)
        db.add_all(system_messages)
        await db.commit()
        await conversation_cache.add_members(group_id,[str(p.user_id) for p in new_participants])

        for msg in system_messages:
            try:
                await broadcast_system_message(group_id, msg, token_user.username)
            except Exception as e:
                print(f"Failed to broadcast add member system message: {e}")
        
        for p in new_participants:
            try:
                await notification_service.send_notification(
                    db=db,
                    user_id=p.user_id,
                    title="Added to Group",
                    body=f"{token_user.username} added you to '{conversation.name or 'Group'}'",
                    type=NotificationType.SYSTEM,
                    data={
                        "conversation_id": str(conversation.id),
                        "sub_event": "conversation.added",
                        "username": token_user.username,
                        "group_name": conversation.name or "Group",
                    }
                )
            except Exception as e:
                print(f"Failed to send add member notification: {e}")
        

    return {
        "message": "Operation completed.",
        "added": len(new_participants),
        "already_members": errors["existing_members"],
        "missing_users": errors["missing_users"],
    }  



@router.post('/leave-group')
async def leave_group(group_id:str,db:DBSession,token:str = Depends(oauth2_scheme)):
    token_user = await user_service.get_current_user(db, token)
    conversation_res = await db.execute(select(Conversation).where(Conversation.id == UUID(group_id)))
    conversation = conversation_res.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404,detail="Group not found")

    if conversation.type != ConversationType.GROUP:
        raise HTTPException(status_code=403,detail="Cannot leave conversation (Not a Group)")

    existing_mem_res = await db.execute(
        select(ConversationParticipant)
        .where(
            ConversationParticipant.user_id == token_user.id,
            ConversationParticipant.conversation_id == UUID(group_id)
        ))
    existing_member = existing_mem_res.scalar_one_or_none()
    if not existing_member:
        raise HTTPException(status_code=403,detail="Not a member of group")

    await db.delete(existing_member)
    db.add(
        Message(
            conversation_id=UUID(group_id),
            sender_id=token_user.id,
            type=MessageType.SYSTEM,
            message=f"{token_user.username} left group"
    ))
    await db.commit()
    await conversation_cache.remove_member(group_id,str(token_user.id))
    return {
        "message": "Left group"
    }

from sqlalchemy.orm import joinedload, aliased

@router.post("/remove-member")
async def remove_member(
    target_id: str,
    group_id: str,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    target_id=UUID(target_id)
    group_id=UUID(group_id)
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

    msg_obj = Message(
        conversation_id=group_id,
        sender_id=token_user.id,
        type=MessageType.SYSTEM,
        message=f"{token_user.username} removed {target_participant.user.username}",
    )
    db.add(msg_obj)

    await db.commit()
    await conversation_cache.remove_member(str(group_id),str(target_id))

    try:
        await broadcast_system_message(group_id, msg_obj, token_user.username)
    except Exception as e:
        print(f"Failed to broadcast remove member system message: {e}")

    try:
        group_obj = await db.get(Conversation, group_id)
        group_name = group_obj.name if group_obj and group_obj.name else "Group"
        await notification_service.send_notification(
            db=db,
            user_id=target_participant.user_id,
            title="Removed from Group",
            body=f"{token_user.username} removed you from '{group_name}'",
            type=NotificationType.SYSTEM,
            data={
                "conversation_id": str(group_id),
                "sub_event": "conversation.removed",
                "username": token_user.username,
                "group_name": group_name,
            }
        )
    except Exception as e:
        print(f"Failed to send remove member notification: {e}")

    return {
        "message": f"{token_user.username} removed {target_participant.user.username}"
    }
    

@router.post('/create-dm')
async def create_dm(db:DBSession,target_id:str,token:str=Depends(oauth2_scheme)):
    token_user = await user_service.get_current_user(db,token)
    if(target_id == token_user.id):
        raise HTTPException(status_code=401,detail="Cannot make a dm yourself")
    target_user = await user_service.get_user_with_id(db,target_id)
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
        .group_by(
            Conversation.id
        )
        .having(
            func.count(
                func.distinct(ConversationParticipant.user_id)
            ) == 2
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
    await conversation_cache.sync_conversation(
        str(dm.id),
        db
    )
    return {
        "message": "DM created",
        "conversation_id": dm.id
    }

def build_latest_message(
    message,
    username,
    delete_state,
    receipt,
    current_user_id,
    display_name=None,
    *,
    is_group: bool,
):
    if not message:
        return None

    is_me = message.sender_id == current_user_id

    if is_me:
        sender = "You"
    elif is_group:
        sender = username.split(" ")[0] if username else None
    else:
        sender = display_name

    return {
        "id": str(message.id),
        "sender_id": (
            str(message.sender_id)
            if message.sender_id
            else None
        ),
        "sender": sender,
        "display_name": display_name,

        "content": (
            "Deleted for everyone"
            if message.is_deleted_global
            else "Deleted for me"
            if delete_state
            else message.message
        ),

        "timestamp": message.timestamp,

        "is_deleted_for_everyone": message.is_deleted_global,
        "is_deleted_for_me": delete_state is not None,

        "is_delivered": (
            receipt is not None
            and receipt.delivered_at is not None
        ),

        "is_read": (
            receipt is not None
            and receipt.read_at is not None
        ),

        "delivered_at": (
            receipt.delivered_at
            if receipt
            else None
        ),

        "read_at": (
            receipt.read_at
            if receipt
            else None
        ),
    }



@router.get('/get-user-groups')
async def get_user_groups(db:DBSession,token:str = Depends(oauth2_scheme)):
    token_user = await user_service.get_current_user(db,token)

    latest_message_subquery = (
        select(
            Message.conversation_id,
            func.max(Message.timestamp).label("latest_time")
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    member_count_subquery = (
        select(func.count(ConversationParticipant.user_id))
        .where(ConversationParticipant.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )

    stmt = (
        select(
            Conversation,
            ConversationParticipant.role,
            Message,
            User.username,
            UserProfile.display_name,
            MessageDeleteState,
            MessageReceipt,
            member_count_subquery.label("member_count"),
        )
        .join(
            ConversationParticipant,
            ConversationParticipant.conversation_id == Conversation.id
        )
        .outerjoin(
            latest_message_subquery,
            latest_message_subquery.c.conversation_id == Conversation.id
        )
        .outerjoin(
            Message,
            (Message.conversation_id == Conversation.id) & (Message.timestamp == latest_message_subquery.c.latest_time)
        )
        .outerjoin(
            MessageDeleteState,
            (MessageDeleteState.message_id == Message.id)
            & (MessageDeleteState.user_id == token_user.id)
        )
        .outerjoin(
            MessageReceipt,
            (MessageReceipt.message_id == Message.id)
            & (MessageReceipt.user_id == token_user.id)
        )
        .outerjoin(
            User,
            User.id == Message.sender_id
        )
        .outerjoin(
            UserProfile,
            UserProfile.user_id == User.id,
        )
        .where(
            ConversationParticipant.user_id == token_user.id,
            Conversation.type == ConversationType.GROUP,
            Conversation.is_deleted == False
        )
    )

    results = await db.execute(stmt)

    groups = results.all()

    return [
        {
            "id": group.id,
            "title": group.name,
            "type": group.type.value,
            "role": role.value,
            "member_count": member_count,
            "latest_message": build_latest_message(
                message=message,
                username=username,
                display_name=display_name,
                delete_state=delete_state,
                receipt=receipt,
                current_user_id=token_user.id,
                is_group=True,
            ),
        }
        for group, role, message, username,display_name, delete_state, receipt, member_count in groups
    ]



@router.get("/get-user-dms")
async def get_user_dms(
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    token_user = await user_service.get_current_user(db, token)

    latest_message_subquery = (
        select(
            Message.conversation_id,
            func.max(Message.timestamp).label("latest_time"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    message_sender = aliased(User)

    stmt = (
        select(
            Conversation,
            User.id.label("other_user_id"),
            User.username,
            UserProfile.display_name,
            Message,
            MessageDeleteState,
            MessageReceipt,
            message_sender.id,
            message_sender.username,
        )
        .join(
            ConversationParticipant,
            ConversationParticipant.conversation_id == Conversation.id,
        )
        .join(
            User,
            User.id == ConversationParticipant.user_id,
        )
        .outerjoin(
            UserProfile,
            UserProfile.user_id == User.id,
        )
        .outerjoin(
            latest_message_subquery,
            latest_message_subquery.c.conversation_id
            == Conversation.id,
        )
        .outerjoin(
            Message,
            (Message.conversation_id == Conversation.id)
            & (
                Message.timestamp
                == latest_message_subquery.c.latest_time
            ),
        )
        .outerjoin(
            MessageDeleteState,
            (MessageDeleteState.message_id == Message.id)
            & (MessageDeleteState.user_id == token_user.id),
        )
        .outerjoin(
            MessageReceipt,
            (MessageReceipt.message_id == Message.id)
            & (MessageReceipt.user_id == token_user.id),
        )
        .outerjoin(
            message_sender,
            message_sender.id == Message.sender_id,
        )
        .where(
            Conversation.type == ConversationType.PERSONAL,
            Conversation.is_deleted == False,
            Conversation.id.in_(
                select(
                    ConversationParticipant.conversation_id
                ).where(
                    ConversationParticipant.user_id
                    == token_user.id
                )
            ),
            ConversationParticipant.user_id != token_user.id,
        )
    )

    result = await db.execute(stmt)

    rows = result.all()

    # Batch-check presence: one Redis call instead of N calls per row
    online_users: set = await r.smembers("online_users")

    # Batch-fetch last_seen for all other users using a pipeline
    from app.redis.keys import RedisKeys as RK

    other_ids = [
        str(row[1]) if row[1] else None
        for row in rows
    ]

    last_seen_map: dict[str, int | None] = {}

    if any(other_ids):
        pipe = r.pipeline()

        for uid in other_ids:
            if uid:
                pipe.get(RK.last_seen(uid))
            else:
                pipe.get("__null__")

        results_ls = await pipe.execute()

        for uid, val in zip(other_ids, results_ls):
            if uid:
                last_seen_map[uid] = (
                    int(val) if val is not None else None
                )

    return [
        {
            "id": conversation.id,
            "name": username,
            "display_name": display_name,
            "type": conversation.type.value,
            "other_user_id": (
                str(other_user_id)
                if other_user_id
                else None
            ),
            "is_online": (
                str(other_user_id) in online_users
                if other_user_id
                else False
            ),
            "last_seen": (
                last_seen_map.get(str(other_user_id))
                if other_user_id
                else None
            ),
            "latest_message": build_latest_message(
                message=message,
                username=latest_sender,
                delete_state=delete_state,
                receipt=receipt,
                current_user_id=token_user.id,
                is_group=False,
            ),
        }
        for (
            conversation,
            other_user_id,
            username,
            display_name,
            message,
            delete_state,
            receipt,
            latest_sender_id,
            latest_sender,
        ) in rows
    ]


@router.delete('/delete-group')
async def delete_group(group_id:str,db:DBSession,token:str = Depends(oauth2_scheme)):
    token_user = await user_service.get_current_user(db,token)
    group_uuid = UUID(group_id)
    isgroup = await db.scalar(
        select(Conversation).where(
            Conversation.id == group_uuid,
            Conversation.type == ConversationType.GROUP,
            Conversation.is_deleted.is_(False)
        )
    )
    if not isgroup:
        raise HTTPException(status_code=404,detail="No group found")
    isparticipant = await db.scalar(
        select(ConversationParticipant).where(ConversationParticipant.user_id == token_user.id,ConversationParticipant.conversation_id == group_uuid)
    )
    if not isparticipant:
        raise HTTPException(status_code=403,detail="You're not part of this group")
    if isparticipant.role not in [ParticipantRole.OWNER,ParticipantRole.ADMIN]:
        raise HTTPException(status_code=403,detail="You're not authorized to perform this action")

    isgroup.is_deleted = True
    await db.commit()
    return {"message": "Group deleted successfully"}
    
@router.delete("/delete-dm")
async def delete_dm(
    dm_id: str,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    token_user = await user_service.get_current_user(db, token)

    try:
        dm_uuid = UUID(dm_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid DM ID"
        )

    # Find the DM
    dm = await db.scalar(
        select(Conversation).where(
            Conversation.id == dm_uuid,
            Conversation.type == ConversationType.PERSONAL,
        )
    )

    if not dm:
        raise HTTPException(
            status_code=404,
            detail="DM not found"
        )

    # Make sure current user is a participant
    participant = await db.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == dm_uuid,
            ConversationParticipant.user_id == token_user.id,
        )
    )

    if not participant:
        raise HTTPException(
            status_code=403,
            detail="You're not part of this DM"
        )

    # Delete participants first
    await db.execute(
        delete(ConversationParticipant).where(
            ConversationParticipant.conversation_id == dm_uuid
        )
    )

    # Delete the conversation itself
    await db.delete(dm)

    await db.commit()

    return {
        "message": "DM deleted successfully",
        "dm_id": str(dm_uuid),
    }

@router.post("/sync-conversations")
async def sync_conversations(
    db: DBSession = None,
):
    result = await conversation_cache.sync_all(db)

    return {
        "success": True,
        "message": "Conversation cache synchronized successfully",
        **result,
    }


@router.get("/search")
async def global_search(q: str, db: DBSession, token: str = Depends(oauth2_scheme)):
    token_user = await user_service.get_current_user(db, token)
    search_term = f"%{q.strip()}%"
    print(search_term)

    users = (
        await db.execute(
            select(
                User.id,
                User.username,
                User.email,
                User.is_active,
                UserProfile.display_name,
                UserProfile.avatar_url,
            )
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .where(
                User.id != token_user.id,
                or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    UserProfile.display_name.ilike(search_term),
                ),
            )
            .limit(20)
        )
    ).mappings().all()

    groups = (
        await db.execute(
            select(
                Conversation.id,
                Conversation.name,
                Conversation.description,
                Conversation.avatar_url,
            )
            .join(ConversationParticipant, ConversationParticipant.conversation_id == Conversation.id)
            .where(
                ConversationParticipant.user_id == token_user.id,
                Conversation.type == ConversationType.GROUP,
                Conversation.is_deleted.is_(False),
                or_(
                    Conversation.name.ilike(search_term),
                    Conversation.description.ilike(search_term),
                ),
            )
            .limit(20)
        )
    ).mappings().all()
    print(groups)
    return {
        "users": [
            {
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "display_name": u.display_name,
                "avatar_url": u.avatar_url,
                "is_active": u.is_active,
            }
            for u in users
        ],
        "groups": [
            {
                "id": str(g.id),
                "name": g.name,
                "description": g.description,
                "avatar_url": g.avatar_url,
            }
            for g in groups
        ],
    }


@router.get('/get-group-members')
async def get_group_members(group_id: str, db: DBSession, token: str = Depends(oauth2_scheme)):
    token_user = await user_service.get_current_user(db, token)
    
    # Check if user is in the group
    is_member = await db.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == UUID(group_id),
            ConversationParticipant.user_id == token_user.id
        )
    )
    if not is_member:
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    mem_res = await db.execute(
        select(
            ConversationParticipant.role,
            ConversationParticipant.joined_at,
            User.id,
            User.username,
            User.email,
            User.is_active,
            UserProfile.avatar_url,
            UserProfile.display_name,
        )
        .join(
            User,
            User.id == ConversationParticipant.user_id
        )
        .outerjoin(
            UserProfile,
            UserProfile.user_id == User.id
        )
        .where(
            ConversationParticipant.conversation_id == UUID(group_id)
        )
    )

    members = mem_res.mappings().all()

    return [
        {
            "id": str(m.id),
            "username": m.username,
            "email": m.email,
            "display_name": m.display_name,
            "avatar_url": m.avatar_url,
            "is_active": m.is_active,
            "role": m.role.value,
            "joined_at": m.joined_at,
        }
        for m in members
    ]


@general_chat_router.get('/get-all-groups')
async def get_all_groups(db:DBSession):
    results = await db.execute(select(Conversation).where(Conversation.type == ConversationType.GROUP))
    conversations = results.scalars().all()
    return conversations


@general_chat_router.get('/get-participant-details')
async def get_participant_details(participant_id:str,group_id:str,db:DBSession):
    try:
        group_uuid = UUID(group_id)
        participant_uuid = UUID(participant_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="One or more IDs are invalid UUIDs.",
        )
    conversation = await db.scalar(
        select(Conversation).where(
            Conversation.id == group_uuid
        )
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Group not found.",
        )

    # Check requester permissions
    result = await db.execute(
        select(
            ConversationParticipant.conversation_id,
            ConversationParticipant.joined_at,
            ConversationParticipant.user_id,
            ConversationParticipant.role,
            ConversationParticipant.last_read_message_id,
            User.email,
            User.username,
            User.created_at,
            User.is_active,
        )
        .join(
            User,
            User.id == ConversationParticipant.user_id,
        )
        .where(
            ConversationParticipant.conversation_id == group_uuid,
            ConversationParticipant.user_id == participant_uuid,
        )
    )

    participant = result.mappings().one_or_none()

    if not participant:
        raise HTTPException(
            status_code=403,
            detail="Participant is not a member of this group.",
        )
    return participant


@general_chat_router.get('/get-all-dms')
async def get_all_dms(db:DBSession):
    results = await db.execute(select(Conversation).where(Conversation.type == ConversationType.PERSONAL))
    conversations = results.scalars().all()
    return conversations
