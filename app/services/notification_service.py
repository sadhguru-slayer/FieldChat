import json
from datetime import datetime, timezone
from typing import Optional, Any
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.models.profile.settings import UserSettings
from app.schema.notification import NotificationResponse, NotificationWSEvent
from app.redis_client import r
from app.redis.keys import RedisKeys


class NotificationService:
    @staticmethod
    async def _check_user_permission(db: AsyncSession, user_id: UUID, notif_type: NotificationType) -> bool:
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await db.execute(stmt)
        settings = result.scalar_one_or_none()

        if not settings:
            return True  # Default to allowed if settings don't exist

        if not settings.notifications_enabled:
            return False

        if notif_type == NotificationType.MESSAGE and not settings.message_notifications:
            return False

        if notif_type == NotificationType.MENTION and not settings.mention_notifications:
            return False

        return True

    @classmethod
    async def send_notification(
        cls,
        db: AsyncSession,
        user_id: UUID,
        title: str,
        body: str,
        type: NotificationType = NotificationType.SYSTEM,
        data: Optional[dict[str, Any]] = None,
    ) -> Optional[NotificationResponse]:
        # Check user notification settings
        allowed = await cls._check_user_permission(db, user_id, type)
        if not allowed:
            return None

        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            data=data or {},
            is_read=False,
        )

        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        resp = NotificationResponse.model_validate(notification)
        ws_event = NotificationWSEvent(notification=resp)

        # Publish to Redis Pub/Sub for WS delivery
        channel = RedisKeys.notification_channel(str(user_id))
        await r.publish(channel, ws_event.model_dump_json())

        return resp

    @classmethod
    async def broadcast_notification(
        cls,
        title: str,
        body: str,
        type: NotificationType = NotificationType.SYSTEM,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        event_payload = {
            "event": "notification",
            "notification": {
                "id": "global",
                "user_id": "broadcast",
                "type": type.value,
                "title": title,
                "body": body,
                "data": data or {},
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        channel = RedisKeys.notifications_global()
        await r.publish(channel, json.dumps(event_payload))

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
        skip: int = 0,
    ) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)

        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: UUID) -> int:
        query = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        user_id: UUID,
        notification_id: Optional[UUID] = None,
        read_all: bool = False,
    ) -> bool:
        if read_all:
            stmt = (
                update(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                )
                .values(is_read=True)
            )
            await db.execute(stmt)
            await db.commit()
            return True

        if notification_id:
            stmt = (
                update(Notification)
                .where(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                )
                .values(is_read=True)
            )
            res = await db.execute(stmt)
            await db.commit()
            return res.rowcount > 0

        return False


notification_service = NotificationService()
