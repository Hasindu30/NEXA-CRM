from typing import Sequence
import re
import unicodedata
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import structlog

from app.modules.workspaces.model import Workspace, WorkspaceMembership
from app.modules.users.model import User
from app.modules.auth.repository import get_user_by_email
from app.modules.workspaces import repository
from app.modules.workspaces.exceptions import (
    WorkspaceNotFoundError,
    AuthorizationError,
    OwnerInvariantError,
    UserNotFoundError,
    DuplicateMembershipError,
)
from app.modules.workspaces.dependencies import WorkspaceContext
from app.modules.workspaces import authorization

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
    workspace_id = uuid.uuid7()
    suffix = str(workspace_id).split('-')[0]
    
    if not base_slug:
        base_slug = f"workspace-{suffix}"
        
    # Try savepoint insert
    try:
        async with db.begin_nested():
            workspace = Workspace(id=workspace_id, name=name, slug=base_slug)
            membership = WorkspaceMembership(user_id=user_id, workspace_id=workspace_id, role=authorization.ROLE_OWNER)
            db.add(workspace)
            db.add(membership)
            await db.flush()
    except IntegrityError as e:
        if "uq_workspaces_slug" in str(e.orig):
            # Fallback using UUID
            fallback_slug = f"{base_slug}-{suffix}"
            async with db.begin_nested():
                # We must recreate the objects because the previous ones were expunged by rollback
                workspace = Workspace(id=workspace_id, name=name, slug=fallback_slug)
                membership = WorkspaceMembership(user_id=user_id, workspace_id=workspace_id, role=authorization.ROLE_OWNER)
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

async def list_members(db: AsyncSession, context: WorkspaceContext):
    authorization.require_permission(context, authorization.PERM_MEMBERS_READ)
    return await repository.list_members(db, context.workspace_id)

async def add_member(db: AsyncSession, context: WorkspaceContext, email: str) -> WorkspaceMembership:
    authorization.require_permission(context, authorization.PERM_MEMBERS_ADD)
    
    target_user = await get_user_by_email(db, email)
    if not target_user:
        raise UserNotFoundError(f"User with email {email} not found")
        
    try:
        async with db.begin_nested():
            membership = await repository.add_membership(
                db, 
                workspace_id=context.workspace_id, 
                user_id=target_user.id, 
                role=authorization.ROLE_MEMBER
            )
            await db.flush()
    except IntegrityError as e:
        if "uq_workspace_memberships" in str(e.orig) or "duplicate key" in str(e.orig):
            raise DuplicateMembershipError(f"User is already a member")
        raise e
        
    await db.commit()
    return membership

async def change_role(db: AsyncSession, context: WorkspaceContext, target_user_id: UUID, new_role: str) -> None:
    authorization.require_permission(context, authorization.PERM_MEMBERS_CHANGE_ROLE)
    
    # Cannot change own role via this endpoint
    if target_user_id == context.user_id:
        raise AuthorizationError("Cannot change your own role")
        
    # Lock workspace
    await repository.lock_workspace_for_membership_mutation(db, context.workspace_id)
    
    target_membership = await repository.get_membership_only(db, context.workspace_id, target_user_id)
    if not target_membership:
        raise WorkspaceNotFoundError("Target user is not a member of this workspace")
        
    if not authorization.can_modify_role(context.membership.role, target_membership.role, new_role):
        raise AuthorizationError("You do not have permission to modify this role")
        
    # If demoting an owner, enforce invariant
    if target_membership.role == authorization.ROLE_OWNER and new_role != authorization.ROLE_OWNER:
        owners = await repository.count_owners(db, context.workspace_id)
        if owners <= 1:
            raise OwnerInvariantError("Cannot demote the final owner of the workspace")
            
    target_membership.role = new_role
    await db.flush()
    await db.commit()

async def remove_member(db: AsyncSession, context: WorkspaceContext, target_user_id: UUID) -> None:
    authorization.require_permission(context, authorization.PERM_MEMBERS_REMOVE)
    
    # Cannot remove self via this endpoint
    if target_user_id == context.user_id:
        raise AuthorizationError("Cannot remove yourself")
        
    # Lock workspace
    await repository.lock_workspace_for_membership_mutation(db, context.workspace_id)
    
    target_membership = await repository.get_membership_only(db, context.workspace_id, target_user_id)
    if not target_membership:
        raise WorkspaceNotFoundError("Target user is not a member of this workspace")
        
    if not authorization.can_remove_member(context.membership.role, target_membership.role):
        raise AuthorizationError("You do not have permission to remove this member")
        
    # If removing an owner, enforce invariant
    if target_membership.role == authorization.ROLE_OWNER:
        owners = await repository.count_owners(db, context.workspace_id)
        if owners <= 1:
            raise OwnerInvariantError("Cannot remove the final owner of the workspace")
            
    await repository.delete_membership(db, context.workspace_id, target_user_id)
    await db.commit()
