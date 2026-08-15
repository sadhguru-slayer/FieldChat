from fastadmin import SqlAlchemyModelAdmin, register
from sqlalchemy import select

from app.core.security.password import password_manager
from app.database import SessionLocal
from app.models.auth.user import User, UserRole


@register(User)
class UserAdmin(SqlAlchemyModelAdmin):
    db_session_maker = SessionLocal

    exclude = ("hashed_password",)

    list_display = (
        "id",
        "username",
        "email",
        "role",
        "is_active",
        "created_at",
    )

    list_display_links = (
        "id",
        "username",
    )

    list_filter = (
        "role",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
    )

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> int | None:

        async with SessionLocal() as session:
            result = await session.execute(
                select(User).where(
                    User.username == username,
                    User.role == UserRole.ADMIN,
                )
            )

            user = result.scalar_one_or_none()

            if not user:
                return None

            if not password_manager.verify_password(
                password,
                user.hashed_password,
            ):
                return None

            return user.id

    async def change_password(
        self,
        id: int,
        password: str,
    ) -> None:

        async with SessionLocal() as session:
            result = await session.execute(
                select(User).where(User.id == id)
            )

            user = result.scalar_one_or_none()

            if not user:
                return

            user.hashed_password = password_manager.hash_password(password)

            await session.commit()