from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.users.model import User
from app.modules.workspaces import service
from app.modules.workspaces.dependencies import get_workspace_context, WorkspaceContext
from app.modules.workspaces.schema import (
    WorkspaceCreate, WorkspaceResponse, WorkspaceListResponse,
    WorkspaceMemberListResponse, AddWorkspaceMemberRequest, ChangeWorkspaceMemberRoleRequest
)
from app.modules.workspaces.exceptions import (
    AuthorizationError, OwnerInvariantError, UserNotFoundError,
    DuplicateMembershipError, WorkspaceNotFoundError,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# ── Phase 5: Workspace CRUD ───────────────────────────────────────────────────

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=WorkspaceResponse
)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    workspace = await service.create_workspace(db, current_user.id, data.name)
    return WorkspaceResponse.model_validate(workspace)


@router.get(
    "",
    response_model=WorkspaceListResponse
)
async def list_workspaces(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    workspaces = await service.list_workspaces(db, current_user.id)
    return WorkspaceListResponse(
        data=[WorkspaceResponse.model_validate(w) for w in workspaces]
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse
)
async def get_workspace(
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)]
):
    return WorkspaceResponse.model_validate(context.workspace)


# ── Phase 6: Membership Management ───────────────────────────────────────────

@router.get(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberListResponse
)
async def list_members(
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    try:
        members = await service.list_members(db, context)
        return WorkspaceMemberListResponse(
            data=[{"user_id": m.user_id, "email": m.email, "role": m.role, "joined_at": m.joined_at} for m in members]
        )
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post(
    "/{workspace_id}/members",
    status_code=status.HTTP_201_CREATED
)
async def add_member(
    data: AddWorkspaceMemberRequest,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    try:
        await service.add_member(db, context, data.email)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateMembershipError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch(
    "/{workspace_id}/members/{user_id}/role",
    status_code=status.HTTP_200_OK
)
async def change_role(
    user_id: UUID,
    data: ChangeWorkspaceMemberRoleRequest,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    if data.role not in ('owner', 'admin', 'member'):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role")

    try:
        await service.change_role(db, context, user_id, data.role)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except OwnerInvariantError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except WorkspaceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_200_OK
)
async def remove_member(
    user_id: UUID,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    try:
        await service.remove_member(db, context, user_id)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except OwnerInvariantError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except WorkspaceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
