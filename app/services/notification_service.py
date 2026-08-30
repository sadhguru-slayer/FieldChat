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
from sqlalchemy.dialects.postgresql import insert


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

        # Also trigger Web Push in the background
        import asyncio
        asyncio.create_task(cls._trigger_web_push(user_id, json.loads(ws_event.model_dump_json())))

        return resp

    @classmethod
    async def _trigger_web_push(cls, user_id: UUID, payload_data: dict):
        from app.models.notification import PushSubscription
        from app.config import settings
        from app.database import SessionLocal
        import json
        import asyncio
        from pywebpush import webpush, WebPushException

        if not settings.VAPID_PRIVATE_KEY:
            return

        claims_email = settings.VAPID_CLAIMS_EMAIL or "admin@fieldchat.com"
        if not claims_email.startswith("mailto:"):
            claims_email = f"mailto:{claims_email}"

        import hashlib
        pub_key_hash = hashlib.sha256(settings.VAPID_PUBLIC_KEY.encode()).hexdigest()
        print(f"[DEBUG] [WebPush] Triggering push for user_id={user_id} with claims_email={claims_email}...")
        print(f"[DEBUG] [WebPush] Active Private Key prefix: {settings.VAPID_PRIVATE_KEY[:10]}...")
        print(f"[DEBUG] [WebPush] Active Public Key prefix: {settings.VAPID_PUBLIC_KEY[:10]}...")
        print(f"[DEBUG] [WebPush] Backend VAPID public key hash: {pub_key_hash}")
        async with SessionLocal() as db:
            stmt = select(PushSubscription).where(PushSubscription.user_id == user_id)
            result = await db.execute(stmt)
            subscriptions = result.scalars().all()

            # Materialize credentials before closing session
            subs_data = [
                {
                    "endpoint": sub.endpoint,
                    "p256dh": sub.p256dh,
                    "auth": sub.auth
                }
                for sub in subscriptions
            ]

        print(f"[DEBUG] [WebPush] Found {len(subs_data)} active push subscriptions for user.")

        endpoints_to_delete = []
        for sub in subs_data:
            def sync_push():
                try:
                    headers = {}
                    if "notify.windows.com" in sub["endpoint"]:
                        headers["X-WNS-Type"] = "wns/raw"

                    webpush(
                        subscription_info={
                            "endpoint": sub["endpoint"],
                            "keys": {
                                "p256dh": sub["p256dh"],
                                "auth": sub["auth"]
                            }
                        },
                        data=json.dumps(payload_data),
                        vapid_private_key=settings.VAPID_PRIVATE_KEY,
                        vapid_claims={"sub": claims_email},
                        headers=headers
                    )
                    print(f"[DEBUG] [WebPush] Push delivered successfully to endpoint: {sub['endpoint'][:60]}...")
                    return False
                except WebPushException as ex:
                    print(f"[WARN] [WebPush] Web push failed for {sub['endpoint'][:60]}: {repr(ex)}")
                    if ex.response is not None and ex.response.status_code in (404, 410):
                        print(f"[DEBUG] [WebPush] Failure is permanent (Status {ex.response.status_code}). Scheduling cleanup.")
                        return True
                    return False

            should_delete = await asyncio.to_thread(sync_push)
            if should_delete:
                endpoints_to_delete.append(sub["endpoint"])

        if endpoints_to_delete:
            print(f"[DEBUG] [WebPush] Deleting {len(endpoints_to_delete)} stale/invalid subscriptions from database...")
            from sqlalchemy import delete
            async with SessionLocal() as db:
                await db.execute(
                    delete(PushSubscription).where(
                        PushSubscription.endpoint.in_(endpoints_to_delete)
                    )
                )
                await db.commit()
            print(f"[DEBUG] [WebPush] Database cleanup finished.")

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

    @staticmethod
    async def save_push_subscription(
        db: AsyncSession,
        user_id: UUID,
        endpoint: str,
        p256dh: str,
        auth: str,
    ) -> bool:
        print(f"[DEBUG] [Service] Saving push subscription for user_id={user_id}...")
        print(f"[DEBUG] [Service] Subscription Keys: p256dh={p256dh[:20]}..., auth={auth[:10]}...")
        from app.models.notification import PushSubscription
        try:
            stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
            result = await db.execute(stmt)
            sub = result.scalar_one_or_none()

            if sub:
                print(f"[DEBUG] [Service] Subscription endpoint exists. Updating keys and user_id...")
                sub.user_id = user_id
                sub.p256dh = p256dh
                sub.auth = auth
            else:
                print(f"[DEBUG] [Service] New subscription endpoint. Creating new record...")
                sub = PushSubscription(
                    user_id=user_id,
                    endpoint=endpoint,
                    p256dh=p256dh,
                    auth=auth,
                )
                db.add(sub)

            await db.commit()
            print(f"[DEBUG] [Service] Save transaction committed successfully in database.")
            return True
        except Exception as e:
            print(f"[ERROR] [Service] Failed to save push subscription in database: {repr(e)}")
            await db.rollback()
            return False


notification_service = NotificationService()
