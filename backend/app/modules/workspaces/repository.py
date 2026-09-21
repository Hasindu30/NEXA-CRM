from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.workspaces.model import Workspace, WorkspaceMembership

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
