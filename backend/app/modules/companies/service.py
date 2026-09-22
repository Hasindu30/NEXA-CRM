from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.modules.companies.model import Company
from app.modules.companies.schema import CompanyCreate, CompanyUpdate, PaginatedCompanyResponse
from app.modules.companies import repository
from app.modules.people.repository import unlink_people_from_company

async def create_company(db: AsyncSession, workspace_id: UUID, data: CompanyCreate) -> Company:
    company = Company(
        workspace_id=workspace_id,
        name=data.name,
        domain=data.domain,
        phone=data.phone,
        website=data.website
    )
    await repository.create_company(db, company)
    await db.commit()
    await db.refresh(company)
    return company

async def get_company(db: AsyncSession, workspace_id: UUID, company_id: UUID) -> Company:
    company = await repository.get_company(db, workspace_id, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company

async def list_companies(
    db: AsyncSession, 
    workspace_id: UUID, 
    q: str | None, 
    page: int, 
    limit: int
) -> PaginatedCompanyResponse:
    skip = (page - 1) * limit
    companies, total = await repository.list_companies(db, workspace_id, q, skip, limit)
    
    return PaginatedCompanyResponse(
        data=companies,
        meta={
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 1
        }
    )

async def update_company(db: AsyncSession, workspace_id: UUID, company_id: UUID, data: CompanyUpdate) -> Company:
    company = await repository.get_company(db, workspace_id, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(company, key, value)
        
    await db.commit()
    await db.refresh(company)
    return company

async def delete_company(db: AsyncSession, workspace_id: UUID, company_id: UUID) -> None:
    # Transactional delete flow
    # 1. Lock the company
    company = await repository.get_company_for_update(db, workspace_id, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        
    # 2. Unlink people
    await unlink_people_from_company(db, workspace_id, company_id)
    
    # 3. Delete company
    await db.delete(company)
    
    # 4. Commit
    await db.commit()
