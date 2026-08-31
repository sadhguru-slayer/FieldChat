from app.models.chat.participants import ConversationParticipant, ParticipantRole
from sqlalchemy import select, delete

from datetime import timezone,datetime
import json

from sqlalchemy import select
from sqlalchemy.orm import  selectinload

from app.ws.manager import manager
# from app.ws.events import WSMessageEvent

from app.models.chat.messages import Message,MessageDeleteState, MessageEvent, MessageReceipt, MessageType, MessageReaction


from app.redis_client import r
from app.redis.keys import RedisKeys
from app.dependencies import DBSession
from app.services.cache_management.conversation import conversation_cache 
from app.services.cache_management.active_users import active_users_cache
from app.schema.chat.message import MessageEventPayload
from uuid import UUID
from app.models.notification import NotificationType
from app.services.notification_service import notification_service
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class ServiceResult(Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None

class MessageService:
    def __init__(self, db):
        self.db = db

    def _build_event(
        self,
        event: MessageEvent,
        message_id,
        conversation_id,
        *,
        sender_id=None,
        user_id=None,
        username=None,
        display_name=None,
        message=None,
        timestamp=None,
        edited_at=None,
        reply_to=None,
        reaction=None,
    old_reaction=None,
        media_url=None,
        media_name=None,
    ):
        return MessageEventPayload(
            event=event,
            message_id=str(message_id),
            conversation_id=str(conversation_id),
            sender_id=str(sender_id) if sender_id else None,
            user_id=str(user_id) if user_id else None,
            username=username,
            display_name=display_name,
            message=message,
            timestamp=(
                timestamp.astimezone(timezone.utc).isoformat()
                if timestamp
                else None
            ),
            edited_at=(
                edited_at.astimezone(timezone.utc).isoformat()
                if edited_at
                else None
            ),
            reply_to=reply_to,
            reaction=reaction,
        old_reaction=old_reaction,
            media_url=media_url,
            media_name=media_name,
        )

    async def _get_reply_preview(self, message_id, user_id):
        stmt = (
            select(Message)
            .options(selectinload(Message.sender))
            .where(Message.id == message_id)
        )

        message = await self.db.scalar(stmt)

        if not message:
            return None

        if message.is_deleted_global:
            return {
                "message_id": str(message.id),
                "sender_id": str(message.sender_id),
                "username": message.sender.username if message.sender else None,
                "message": "Deleted for everyone",
                "timestamp": (
                    message.timestamp.astimezone(timezone.utc).isoformat()
                    if message.timestamp
                    else None
                ),
                "type": message.type.value,
                "is_deleted": True,
            }

        return {
            "message_id": str(message.id),
            "sender_id": (
                str(message.sender_id)
                if message.type != MessageType.SYSTEM
                else "SYSTEM"
            ),
            "username": (
                message.sender.username
                if message.sender and message.type != MessageType.SYSTEM
                else "SYSTEM"
            ),
            "message": message.message,
            "timestamp": (
                message.timestamp.astimezone(timezone.utc).isoformat()
                if message.timestamp
                else None
            ),
            "type": message.type.value,
            "is_deleted": False,
        }


    async def create_message(
        self,
        user,
        conversation_id,
        content,
        reply_to_message_id=None,
        media_url=None,
        media_name=None,
    ):
        if not await conversation_cache.is_member(
            str(conversation_id),
            str(user.id),
        ):
            return ServiceResult(
                success=False,
                error="NOT_CONVERSATION_MEMBER",
            )

        if content:
            content = content.strip()
        else:
            content = ""

        if not content and not media_url:
            return ServiceResult(
                success=False,
                error="EMPTY_MESSAGE",
            )

        reply_to = None

        if reply_to_message_id:
            stmt = (
                select(Message)
                .options(selectinload(Message.sender))
                .where(
                    Message.id == reply_to_message_id,
                    Message.conversation_id == conversation_id,
                )
            )

            reply_to = await self.db.scalar(stmt)

            if not reply_to:
                return ServiceResult(
                    success=False,
                    error="REPLY_MESSAGE_NOT_FOUND",
                )

        db_message = Message(
            conversation_id=conversation_id,
            sender_id=user.id,
            message=content,
            reply_to_message_id=reply_to.id if reply_to else None,
            media_url=media_url,
            media_name=media_name,
        )

        self.db.add(db_message)
        await self.db.commit()
        await self.db.refresh(db_message)

        reply_preview = None

        if reply_to:
            reply_preview = {
                "message_id": str(reply_to.id),
                "sender_id": (
                    str(reply_to.sender_id)
                    if reply_to.type != MessageType.SYSTEM
                    else "SYSTEM"
                ),
                "username": (
                    reply_to.sender.username
                    if reply_to.sender and reply_to.type != MessageType.SYSTEM
                    else "SYSTEM"
                ),
                "message": (
                    "Deleted for everyone"
                    if reply_to.is_deleted_global
                    else reply_to.message
                ),
                "timestamp": (
                    reply_to.timestamp.astimezone(timezone.utc).isoformat()
                    if reply_to.timestamp
                    else None
                ),
                "type": reply_to.type.value,
                "is_deleted": reply_to.is_deleted_global,
            }

        event_payload = self._build_event(
            MessageEvent.MESSAGE_CREATED,
            db_message.id,
            conversation_id,
            sender_id=user.id,
            username=user.username,
            display_name=user.profile.display_name if user.profile else None,
            message=content,
            timestamp=db_message.timestamp,
            reply_to=reply_preview,
            media_url=db_message.media_url,
            media_name=db_message.media_name,
        )

        await r.publish(
            RedisKeys.conversation_key(str(conversation_id)),
            event_payload.model_dump_json(),
        )

        try:
            stmt = select(ConversationParticipant.user_id).where(
                ConversationParticipant.conversation_id == UUID(str(conversation_id)),
                ConversationParticipant.user_id != user.id,
            )
            other_members = (await self.db.execute(stmt)).scalars().all()
            
            notif_body = content
            if not notif_body and db_message.media_url:
                is_image = any(db_message.media_name.lower().endswith(ext) for ext in [".jpeg", ".jpg", ".gif", ".png", ".webp", ".svg"]) if db_message.media_name else False
                notif_body = "📷 Photo" if is_image else "📁 Attachment"

            for member_id in other_members:
                # Do not send notifications to users actively viewing this conversation
                if await active_users_cache.is_user_active(str(conversation_id), str(member_id)):
                    continue

                await notification_service.send_notification(
                    db=self.db,
                    user_id=member_id,
                    title=f"New message from {user.username}",
                    body=notif_body[:100] + ("..." if len(notif_body) > 100 else "") if notif_body else "",
                    type=NotificationType.MESSAGE,
                    data={
                        "conversation_id": str(conversation_id),
                        "message_id": str(db_message.id),
                        "sender_id": str(user.id),
                        "username": user.username,
                    },
                )
        except Exception as e:
            print(f"[Notification Error] Failed to send message notification: {e}")

        return ServiceResult(
            success=True,
            data=event_payload,
        )


    async def edit_message(
        self,
        user,
        conversation_id,
        message_id,
        content,
    ):
        if not await conversation_cache.is_member(
            str(conversation_id),
            str(user.id),
        ):
            return ServiceResult(
                success=False,
                error="NOT_CONVERSATION_MEMBER",
            )

        if not content or not content.strip():
            return ServiceResult(
                success=False,
                error="EMPTY_MESSAGE",
            )

        stmt = select(Message).where(
            Message.id == message_id,
            Message.conversation_id == conversation_id,
        )

        result = await self.db.execute(stmt)
        message = result.scalar_one_or_none()

        if not message:
            return ServiceResult(
                success=False,
                error="MESSAGE_NOT_FOUND",
            )

        if message.sender_id != user.id:
            return ServiceResult(
                success=False,
                error="NOT_MESSAGE_OWNER",
            )

        if message.is_deleted_global:
            return ServiceResult(
                success=False,
                error="MESSAGE_DELETED",
            )

        message.message = content.strip()
        message.edited_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(message)

        event_payload = self._build_event(
            MessageEvent.MESSAGE_EDITED,
            message.id,
            conversation_id,
            sender_id=user.id,
            username=user.username,
            display_name=user.profile.display_name if user.profile else None,
            message=content,
            timestamp=message.timestamp,
            edited_at=message.edited_at,
        )
        await r.publish(
            f"conversation:{conversation_id}",
            event_payload.model_dump_json(),
        )   

        return ServiceResult(
            success=True,
            data=event_payload,
        )

    async def message_deleted_for_everyone(
        self,
        user,
        conversation_id,
        message_id,
    ):
        if not conversation_id or not message_id:
            return ServiceResult(
                success=False,
                error="NOT_ENOUGH_PARAMETERS",
            )

        if not await conversation_cache.is_member(
            str(conversation_id),
            str(user.id),
        ):
            return ServiceResult(
                success=False,
                error="NOT_CONVERSATION_MEMBER",
            )

        stmt = select(Message).where(
            Message.id == message_id,
            Message.conversation_id == conversation_id,
        )

        result = await self.db.execute(stmt)
        message = result.scalar_one_or_none()

        if not message:
            return ServiceResult(
                success=False,
                error="MESSAGE_NOT_FOUND",
            )

        # Get participant role
        role_stmt = select(ConversationParticipant.role).where(
            ConversationParticipant.user_id == user.id,
            ConversationParticipant.conversation_id == conversation_id,
        )

        role_result = await self.db.execute(role_stmt)
        participant_role = role_result.scalar_one_or_none()

        # Only sender, admin, or owner can delete for everyone
        if (
            message.sender_id != user.id
            and participant_role not in (
                ParticipantRole.ADMIN,
                ParticipantRole.OWNER,
            )
        ):
            return ServiceResult(
                success=False,
                error="NOT_ALLOWED_TO_DELETE_FOR_EVERYONE",
            )

        if message.is_deleted_global:
            return ServiceResult(
                success=False,
                error="MESSAGE_ALREADY_DELETED",
            )

        message.is_deleted_global = True

        if message.media_url:
            try:
                from app.services.storage_service import StorageService
                StorageService().delete_media_by_url(message.media_url)
            except Exception as e:
                print(f"[Storage Error] Failed to delete media for message {message.id}: {e}")
            message.media_url = None
            message.media_name = None

        await self.db.commit()
        await self.db.refresh(message)

        event_payload = self._build_event(
            MessageEvent.MESSAGE_DELETED_FOR_EVERYONE,
            message.id,
            conversation_id,
            sender_id=message.sender_id,
            message="Deleted for everyone",
            timestamp=message.timestamp,
        )

        await r.publish(
            RedisKeys.conversation_key(str(conversation_id)),
            event_payload.model_dump_json(),
        )

        return ServiceResult(
            success=True,
            data=event_payload,
        )

    async def message_delete_for_me(
        self,
        user,
        conversation_id,
        message_id,
    ):
        if not conversation_id or not message_id:
            return ServiceResult(
                success=False,
                error="NOT_ENOUGH_PARAMETERS",
            )

        if not await conversation_cache.is_member(
            str(conversation_id),
            str(user.id),
        ):
            return ServiceResult(
                success=False,
                error="NOT_CONVERSATION_MEMBER",
            )

        stmt = select(Message).where(
            Message.id == message_id,
            Message.conversation_id == conversation_id,
        )

        result = await self.db.execute(stmt)
        message = result.scalar_one_or_none()

        if not message:
            return ServiceResult(
                success=False,
                error="MESSAGE_NOT_FOUND",
            )

        stmt = select(MessageDeleteState).where(
            MessageDeleteState.message_id == message_id,
            MessageDeleteState.user_id == user.id,
        )

        existing = (
            await self.db.execute(stmt)
        ).scalar_one_or_none()

        if existing:
            return ServiceResult(
                success=False,
                error="MESSAGE_ALREADY_DELETED",
            )

        delete_state = MessageDeleteState(
            message_id=message.id,
            user_id=user.id,
        )

        self.db.add(delete_state)
        await self.db.commit()

        event_payload = self._build_event(
            MessageEvent.MESSAGE_DELETED_FOR_ME,
            message.id,
            conversation_id,
            user_id=user.id,
        )

        await r.publish(
            f"user:{user.id}",
            event_payload.model_dump_json(),
        )

        return ServiceResult(
            success=True,
            data=event_payload,
        )

    async def clear_chat(self, user_id, conversation_id):
        # Fetch all messages with media URLs in this conversation
        stmt = select(Message.media_url).where(
            Message.conversation_id == conversation_id,
            Message.media_url.isnot(None),
        )
        media_urls = (await self.db.execute(stmt)).scalars().all()
        
        # Delete from MinIO
        if media_urls:
            try:
                from app.services.storage_service import StorageService
                storage_service = StorageService()
                for url in media_urls:
                    if url:
                        storage_service.delete_media_by_url(url)
            except Exception as e:
                print(f"[Storage Error] Failed to delete media on clear_chat: {e}")

        # Delete all messages from database
        await self.db.execute(
            delete(Message).where(
                Message.conversation_id == conversation_id
            )
        )

        """The below code should be implemented later for soft deleting/clear_chat"""
        # stmt = select(Message.id).where(
        #     Message.conversation_id == conversation_id
        # )
        # message_ids = (await self.db.execute(stmt)).scalars().all()
        # for message in messages:
        #     delete_state = MessageDeleteState(
        #         message_id=message.id,
        #         user_id=user_id,
        #     )
        #     self.db.add(delete_state)
        await self.db.commit()
        return ServiceResult(success=True, data=True)

    async def mark_delivered(self, user, conversation_id, message_id):
        if not conversation_id or not message_id:
            return ServiceResult(success=False, error="NOT_ENOUGH_PARAMETERS")

        if not await conversation_cache.is_member(
            str(conversation_id),
            str(user.id),
        ):
            return ServiceResult(success=False, error="NOT_CONVERSATION_MEMBER")

        stmt = select(Message).where(
            Message.id == message_id,
            Message.conversation_id == conversation_id,
        )
        message = (await self.db.execute(stmt)).scalar_one_or_none()

        if not message:
            return ServiceResult(success=False, error="MESSAGE_NOT_FOUND")

        if message.sender_id == user.id:
            return ServiceResult(
                success=False,
                error="CANNOT_RECEIPT_OWN_MESSAGE",
            )

        stmt = select(MessageReceipt).where(
            MessageReceipt.message_id == message.id,
            MessageReceipt.user_id == user.id,
        )
        receipt = (await self.db.execute(stmt)).scalar_one_or_none()

        if receipt and receipt.delivered_at is not None:
            return ServiceResult(success=True, data=receipt)

        now = datetime.now(timezone.utc)

        if not receipt:
            receipt = MessageReceipt(
                message_id=message.id,
                user_id=user.id,
                delivered_at=now,
            )
            self.db.add(receipt)
        else:
            receipt.delivered_at = now

        await self.db.commit()
        await self.db.refresh(receipt)

        event_payload = self._build_event(
            MessageEvent.MESSAGE_DELIVERED,
            message.id,
            conversation_id,
            sender_id=message.sender_id,
            user_id=user.id,
            timestamp=receipt.delivered_at,
        )

        # Receipt goes to the original sender
        await r.publish(
            RedisKeys.user_chanel(str(message.sender_id)),
            event_payload.model_dump_json(),
        )

        return ServiceResult(success=True, data=receipt)


    async def mark_read(self, user, conversation_id, message_id):
        if not conversation_id or not message_id:
            return ServiceResult(success=False, error="NOT_ENOUGH_PARAMETERS")

        if not await conversation_cache.is_member(
            str(conversation_id),
            str(user.id),
        ):
            return ServiceResult(success=False, error="NOT_CONVERSATION_MEMBER")

        stmt = select(Message).where(
            Message.id == message_id,
            Message.conversation_id == conversation_id,
        )
        message = (await self.db.execute(stmt)).scalar_one_or_none()

        if not message:
            return ServiceResult(success=False, error="MESSAGE_NOT_FOUND")

        if message.sender_id == user.id:
            return ServiceResult(
                success=False,
                error="CANNOT_RECEIPT_OWN_MESSAGE",
            )

        stmt = select(MessageReceipt).where(
            MessageReceipt.message_id == message.id,
            MessageReceipt.user_id == user.id,
        )
        receipt = (await self.db.execute(stmt)).scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if not receipt:
            receipt = MessageReceipt(
                message_id=message.id,
                user_id=user.id,
                delivered_at=now,
                read_at=now,
            )
            self.db.add(receipt)

        else:
            if receipt.read_at is not None:
                return ServiceResult(success=True, data=receipt)

            if receipt.delivered_at is None:
                receipt.delivered_at = now

            receipt.read_at = now

        await self.db.commit()
        await self.db.refresh(receipt)

        event_payload = self._build_event(
            MessageEvent.MESSAGE_READ,
            message.id,
            conversation_id,
            sender_id=message.sender_id,
            user_id=user.id,
            timestamp=receipt.read_at,
        )

        # Receipt goes to the original sender
        await r.publish(
            RedisKeys.user_chanel(str(message.sender_id)),
            event_payload.model_dump_json(),
        )

        return ServiceResult(success=True, data=receipt)


    async def mark_all_read(self, user, conversation_id):
        if not conversation_id:
            return ServiceResult(success=False, error="NOT_ENOUGH_PARAMETERS")

        if not await conversation_cache.is_member(
            str(conversation_id),
            str(user.id),
        ):
            return ServiceResult(success=False, error="NOT_CONVERSATION_MEMBER")

        # Find all messages in this conversation not sent by this user, where they don't have a read receipt yet
        stmt = (
            select(Message)
            .outerjoin(
                MessageReceipt,
                (MessageReceipt.message_id == Message.id)
                & (MessageReceipt.user_id == user.id)
            )
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_id != user.id,
                MessageReceipt.read_at.is_(None)
            )
        )
        messages = (await self.db.execute(stmt)).scalars().all()

        if not messages:
            return ServiceResult(success=True, data=True)

        now = datetime.now(timezone.utc)

        # For each message, check if receipt exists, otherwise create it
        for message in messages:
            stmt = select(MessageReceipt).where(
                MessageReceipt.message_id == message.id,
                MessageReceipt.user_id == user.id,
            )
            receipt = (await self.db.execute(stmt)).scalar_one_or_none()

            if not receipt:
                receipt = MessageReceipt(
                    message_id=message.id,
                    user_id=user.id,
                    delivered_at=now,
                    read_at=now,
                )
                self.db.add(receipt)
            else:
                if not receipt.delivered_at:
                    receipt.delivered_at = now
                receipt.read_at = now

        await self.db.commit()

        # Let's broadcast MESSAGE_READ event for each message
        for message in messages:
            event_payload = self._build_event(
                MessageEvent.MESSAGE_READ,
                message.id,
                conversation_id,
                sender_id=message.sender_id,
                user_id=user.id,
                timestamp=now,
            )
            await r.publish(
                RedisKeys.conversation_key(str(conversation_id)),
                event_payload.model_dump_json(),
            )

        return ServiceResult(success=True, data=True)


    async def add_reaction(self, user, conversation_id, message_id, reaction):
        if not await conversation_cache.is_member(str(conversation_id), str(user.id)):
            return ServiceResult(success=False, error="NOT_CONVERSATION_MEMBER")

        reaction = reaction.strip()
        if not reaction:
            return ServiceResult(success=False, error="EMPTY_REACTION")
        if len(reaction) > 32:
            return ServiceResult(success=False, error="REACTION_TOO_LONG")

        message = await self.db.scalar(
            select(Message).where(
                Message.id == message_id,
                Message.conversation_id == conversation_id,
            )
        )
        if not message:
            return ServiceResult(success=False, error="MESSAGE_NOT_FOUND")
        if message.is_deleted_global:
            return ServiceResult(success=False, error="MESSAGE_DELETED")

        existing = await self.db.scalar(
            select(MessageReaction).where(
                MessageReaction.message_id == message_id,
                MessageReaction.user_id == user.id,
            )
        )

        if existing and existing.reaction == reaction:
            return ServiceResult(success=True, data=None)

        if existing:
            existing.reaction = reaction
            existing.created_at = datetime.now(timezone.utc)
        else:
            existing = MessageReaction(
                message_id=message.id,
                user_id=user.id,
                reaction=reaction,
            )
            self.db.add(existing)

        await self.db.commit()
        await self.db.refresh(existing)

        event_payload = self._build_event(
            MessageEvent.MESSAGE_REACTION_ADDED,
            message.id,
            conversation_id,
            user_id=user.id,
            reaction=reaction,
        )

        await r.publish(
            RedisKeys.conversation_key(str(conversation_id)),
            event_payload.model_dump_json(),
        )

        # print(event_payload)

        return ServiceResult(success=True, data=event_payload)


    async def remove_reaction(self, user, conversation_id, message_id):
        if not await conversation_cache.is_member(str(conversation_id), str(user.id)):
            return ServiceResult(success=False, error="NOT_CONVERSATION_MEMBER")

        message = await self.db.scalar(
            select(Message).where(
                Message.id == message_id,
                Message.conversation_id == conversation_id,
            )
        )
        if not message:
            return ServiceResult(success=False, error="MESSAGE_NOT_FOUND")

        existing = await self.db.scalar(
            select(MessageReaction).where(
                MessageReaction.message_id == message_id,
                MessageReaction.user_id == user.id,
            )
        )
        if not existing:
            return ServiceResult(success=False, error="REACTION_NOT_FOUND")

        reaction = existing.reaction
        await self.db.delete(existing)
        await self.db.commit()

        event_payload = self._build_event(
            MessageEvent.MESSAGE_REACTION_REMOVED,
            message.id,
            conversation_id,
            user_id=user.id,
            reaction=reaction,
        )

        await r.publish(
            RedisKeys.conversation_key(str(conversation_id)),
            event_payload.model_dump_json(),
        )


        return ServiceResult(success=True, data=event_payload)

    async def mark_all_undelivered_as_delivered(self, user):
        from sqlalchemy import and_, or_
        # 1. Get all conversations the user is in
        conversations_stmt = select(ConversationParticipant.conversation_id).where(
            ConversationParticipant.user_id == user.id
        )
        conversation_ids = (await self.db.execute(conversations_stmt)).scalars().all()
        if not conversation_ids:
            return

        # 2. Find all messages in these conversations that were:
        #    - NOT sent by the current user
        #    - AND have not been deleted globally
        #    - AND do NOT already have a MessageReceipt with delivered_at for this user
        undelivered_stmt = (
            select(Message)
            .outerjoin(
                MessageReceipt,
                and_(
                    MessageReceipt.message_id == Message.id,
                    MessageReceipt.user_id == user.id,
                )
            )
            .where(
                and_(
                    Message.conversation_id.in_(conversation_ids),
                    Message.sender_id != user.id,
                    Message.is_deleted_global == False,
                    or_(
                        MessageReceipt.id.is_(None),
                        MessageReceipt.delivered_at.is_(None)
                    )
                )
            )
        )
        undelivered_messages = (await self.db.execute(undelivered_stmt)).scalars().all()
        if not undelivered_messages:
            return

        now = datetime.now(timezone.utc)
        
        for message in undelivered_messages:
            receipt_stmt = select(MessageReceipt).where(
                and_(
                    MessageReceipt.message_id == message.id,
                    MessageReceipt.user_id == user.id,
                )
            )
            receipt = (await self.db.execute(receipt_stmt)).scalar_one_or_none()
            if not receipt:
                receipt = MessageReceipt(
                    message_id=message.id,
                    user_id=user.id,
                    delivered_at=now,
                )
                self.db.add(receipt)
            else:
                receipt.delivered_at = now
                
            await self.db.commit()
            await self.db.refresh(receipt)

            event_payload = self._build_event(
                MessageEvent.MESSAGE_DELIVERED,
                message.id,
                message.conversation_id,
                sender_id=message.sender_id,
                user_id=user.id,
                timestamp=receipt.delivered_at,
            )

            # Receipt goes to the original sender
            await r.publish(
                RedisKeys.user_chanel(str(message.sender_id)),
                event_payload.model_dump_json(),
            )
