from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.workspaces.dependencies import get_workspace_context, WorkspaceContext
from app.modules.workspaces import authorization
from app.modules.companies import schema, service

router = APIRouter(prefix="/workspaces/{workspace_id}/companies", tags=["companies"])

@router.post("", status_code=status.HTTP_201_CREATED, response_model=schema.CompanyResponse)
async def create_company(
    workspace_id: UUID,
    data: schema.CompanyCreate,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    authorization.require_permission(context, authorization.PERM_COMPANIES_WRITE)
    return await service.create_company(db, workspace_id, data)

@router.get("", response_model=schema.PaginatedCompanyResponse)
async def list_companies(
    workspace_id: UUID,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    q: str | None = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page")
):
    authorization.require_permission(context, authorization.PERM_COMPANIES_READ)
    return await service.list_companies(db, workspace_id, q, page, limit)

@router.get("/{company_id}", response_model=schema.CompanyResponse)
async def get_company(
    workspace_id: UUID,
    company_id: UUID,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    authorization.require_permission(context, authorization.PERM_COMPANIES_READ)
    return await service.get_company(db, workspace_id, company_id)

@router.patch("/{company_id}", response_model=schema.CompanyResponse)
async def update_company(
    workspace_id: UUID,
    company_id: UUID,
    data: schema.CompanyUpdate,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    authorization.require_permission(context, authorization.PERM_COMPANIES_WRITE)
    return await service.update_company(db, workspace_id, company_id, data)

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    workspace_id: UUID,
    company_id: UUID,
    context: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    authorization.require_permission(context, authorization.PERM_COMPANIES_WRITE)
    await service.delete_company(db, workspace_id, company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
