import re
import unicodedata
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import structlog

from app.modules.workspaces.model import Workspace, WorkspaceMembership
from app.modules.workspaces import repository
from app.modules.workspaces.exceptions import WorkspaceNotFoundError

logger = structlog.get_logger()

def _slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

from uuid import UUID
import uuid

async def create_workspace(db: AsyncSession, user_id: UUID, name: str) -> Workspace:
    base_slug = _slugify(name)
    if not base_slug:
        base_slug = "workspace"
        
    workspace_id = uuid.uuid7()
    
    # Try savepoint insert
    try:
        async with db.begin_nested():
            workspace = Workspace(id=workspace_id, name=name, slug=base_slug)
            membership = WorkspaceMembership(user_id=user_id, workspace_id=workspace_id)
            db.add(workspace)
            db.add(membership)
            await db.flush()
    except IntegrityError as e:
        if "uq_workspaces_slug" in str(e.orig):
            # Fallback using UUID
            suffix = str(workspace_id).split('-')[0] # first 8 chars of UUID
            fallback_slug = f"{base_slug}-{suffix}"
            async with db.begin_nested():
                # We must recreate the objects because the previous ones were expunged by rollback
                workspace = Workspace(id=workspace_id, name=name, slug=fallback_slug)
                membership = WorkspaceMembership(user_id=user_id, workspace_id=workspace_id)
                db.add(workspace)
                db.add(membership)
                await db.flush()
        else:
            raise e
            
    await db.commit()
    return workspace

async def get_workspace_context(
    db: AsyncSession, 
    workspace_id: UUID, 
    user_id: UUID
) -> tuple[Workspace, WorkspaceMembership]:
    result = await repository.get_workspace_membership(db, workspace_id, user_id)
    if not result:
        raise WorkspaceNotFoundError()
    return result

async def list_workspaces(db: AsyncSession, user_id: UUID) -> list[Workspace]:
    return await repository.list_workspaces_for_user(db, user_id)
