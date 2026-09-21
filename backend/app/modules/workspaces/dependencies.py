from dataclasses import dataclass
from uuid import UUID
from typing import Annotated
from fastapi import Depends, Path, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.users.model import User
from app.modules.workspaces.model import Workspace, WorkspaceMembership
from app.modules.workspaces import service
from app.modules.workspaces.exceptions import WorkspaceNotFoundError

@dataclass(frozen=True)
class WorkspaceContext:
    user_id: UUID
    workspace_id: UUID
    workspace: Workspace
    membership: WorkspaceMembership

async def get_workspace_context(
    workspace_id: Annotated[UUID, Path(..., description="The unique UUID of the workspace.")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
) -> WorkspaceContext:
    try:
        workspace, membership = await service.get_workspace_context(db, workspace_id, current_user.id)
    except WorkspaceNotFoundError:
        # Same safe 404 for nonexistent and unauthorized workspaces
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
        
    return WorkspaceContext(
        user_id=current_user.id,
        workspace_id=workspace_id,
        workspace=workspace,
        membership=membership
    )
