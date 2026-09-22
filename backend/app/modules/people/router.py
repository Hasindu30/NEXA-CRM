from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.workspaces.dependencies import get_workspace_context, WorkspaceContext
from app.modules.workspaces import authorization
from app.modules.people import schema, service

router = APIRouter(prefix="/workspaces/{workspace_id}/people", tags=["people"])

@router.post("", status_code=status.HTTP_201_CREATED, response_model=schema.PersonResponse)
async def create_person(
    workspace_id: UUID,
    data: schema.PersonCreate,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    authorization.require_permission(context, authorization.PERM_PEOPLE_WRITE)
    return await service.create_person(db, workspace_id, data)

@router.get("", response_model=schema.PaginatedPersonResponse)
async def list_people(
    workspace_id: UUID,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    q: str | None = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page")
):
    authorization.require_permission(context, authorization.PERM_PEOPLE_READ)
    return await service.list_people(db, workspace_id, q, page, limit)

@router.get("/{person_id}", response_model=schema.PersonResponse)
async def get_person(
    workspace_id: UUID,
    person_id: UUID,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    authorization.require_permission(context, authorization.PERM_PEOPLE_READ)
    return await service.get_person(db, workspace_id, person_id)

@router.patch("/{person_id}", response_model=schema.PersonResponse)
async def update_person(
    workspace_id: UUID,
    person_id: UUID,
    data: schema.PersonUpdate,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    authorization.require_permission(context, authorization.PERM_PEOPLE_WRITE)
    return await service.update_person(db, workspace_id, person_id, data)

@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(
    workspace_id: UUID,
    person_id: UUID,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    authorization.require_permission(context, authorization.PERM_PEOPLE_WRITE)
    await service.delete_person(db, workspace_id, person_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
