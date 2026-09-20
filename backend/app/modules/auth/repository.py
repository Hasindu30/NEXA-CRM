from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.model import User
from app.modules.auth.model import PasswordCredential, AuthSession, RefreshToken

async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def get_user_with_password_by_email(session: AsyncSession, email: str) -> tuple[User | None, PasswordCredential | None]:
    stmt = (
        select(User, PasswordCredential)
        .join(PasswordCredential, User.id == PasswordCredential.user_id)
        .where(User.email == email)
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None, None
    return row[0], row[1]

async def create_user(session: AsyncSession, user: User, credential: PasswordCredential) -> None:
    session.add(user)
    session.add(credential)

async def create_auth_session(session: AsyncSession, auth_session: AuthSession, refresh_token: RefreshToken) -> None:
    session.add(auth_session)
    session.add(refresh_token)

async def get_refresh_token_for_update(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    stmt = (
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def revoke_auth_session(session: AsyncSession, session_id: UUID, revoked_at) -> None:
    stmt = (
        update(AuthSession)
        .where(AuthSession.id == session_id)
        .values(revoked_at=revoked_at)
    )
    await session.execute(stmt)

async def get_auth_session(session: AsyncSession, session_id: UUID) -> AuthSession | None:
    stmt = select(AuthSession).where(AuthSession.id == session_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
