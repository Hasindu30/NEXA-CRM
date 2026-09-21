from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.users.model import User
from app.modules.workspaces.schema import WorkspaceCreate, WorkspaceResponse, WorkspaceListResponse
from app.modules.workspaces import service
from app.modules.workspaces.dependencies import get_workspace_context, WorkspaceContext

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

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
