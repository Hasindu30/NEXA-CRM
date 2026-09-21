from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workspaces.model import Workspace, WorkspaceMembership
from app.modules.users.model import User

async def create_workspace_with_membership(
    db: AsyncSession, 
    workspace: Workspace, 
    membership: WorkspaceMembership
) -> None:
    db.add(workspace)
    db.add(membership)
    await db.flush()

async def get_workspace_membership(
    db: AsyncSession, 
    workspace_id: UUID, 
    user_id: UUID
) -> tuple[Workspace, WorkspaceMembership] | None:
    stmt = (
        sa.select(Workspace, WorkspaceMembership)
        .join(WorkspaceMembership, Workspace.id == WorkspaceMembership.workspace_id)
        .where(
            Workspace.id == workspace_id,
            WorkspaceMembership.user_id == user_id
        )
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None
    return row._tuple()

async def list_workspaces_for_user(
    db: AsyncSession, 
    user_id: UUID
) -> list[Workspace]:
    stmt = (
        sa.select(Workspace)
        .join(WorkspaceMembership, Workspace.id == WorkspaceMembership.workspace_id)
        .where(WorkspaceMembership.user_id == user_id)
        .order_by(Workspace.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def lock_workspace_for_membership_mutation(db: AsyncSession, workspace_id: UUID) -> Workspace:
    # Lock the workspace row to serialize membership mutations (role changes/removals)
    stmt = sa.select(Workspace).where(Workspace.id == workspace_id).with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one()

async def list_members(db: AsyncSession, workspace_id: UUID):
    # Returns rows containing user_id, email, role, joined_at
    stmt = (
        sa.select(
            User.id.label("user_id"),
            User.email,
            WorkspaceMembership.role,
            WorkspaceMembership.created_at.label("joined_at")
        )
        .join(WorkspaceMembership, User.id == WorkspaceMembership.user_id)
        .where(WorkspaceMembership.workspace_id == workspace_id)
        .order_by(WorkspaceMembership.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.all()

async def get_membership_with_user(db: AsyncSession, workspace_id: UUID, user_id: UUID) -> tuple[WorkspaceMembership, User] | None:
    stmt = (
        sa.select(WorkspaceMembership, User)
        .join(User, User.id == WorkspaceMembership.user_id)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id
        )
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None
    return row._tuple()

async def get_membership_only(db: AsyncSession, workspace_id: UUID, user_id: UUID) -> WorkspaceMembership | None:
    stmt = sa.select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.user_id == user_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def count_owners(db: AsyncSession, workspace_id: UUID) -> int:
    stmt = sa.select(sa.func.count()).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.role == "owner"
    )
    result = await db.execute(stmt)
    return result.scalar_one()

async def add_membership(db: AsyncSession, workspace_id: UUID, user_id: UUID, role: str) -> WorkspaceMembership:
    membership = WorkspaceMembership(workspace_id=workspace_id, user_id=user_id, role=role)
    db.add(membership)
    await db.flush()
    return membership

async def delete_membership(db: AsyncSession, workspace_id: UUID, user_id: UUID) -> None:
    stmt = sa.delete(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.user_id == user_id
    )
    await db.execute(stmt)
    await db.flush()
