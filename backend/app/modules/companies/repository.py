from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.companies.model import Company

async def create_company(db: AsyncSession, company: Company) -> Company:
    db.add(company)
    return company

async def get_company(db: AsyncSession, workspace_id: UUID, company_id: UUID) -> Company | None:
    stmt = select(Company).where(
        Company.workspace_id == workspace_id,
        Company.id == company_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def list_companies(
    db: AsyncSession, 
    workspace_id: UUID, 
    q: str | None = None, 
    skip: int = 0, 
    limit: int = 50
) -> tuple[list[Company], int]:
    
    # Base query for data
    stmt = select(Company).where(Company.workspace_id == workspace_id)
    
    # Base query for count
    count_stmt = select(func.count()).select_from(Company).where(Company.workspace_id == workspace_id)
    
    if q:
        q = q.strip()
        if q:
            search_filter = Company.name.ilike(f"%{q}%") | Company.domain.ilike(f"%{q}%")
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)
            
    # Apply ordering and pagination to data query
    stmt = stmt.order_by(Company.created_at.desc(), Company.id.desc())
    stmt = stmt.offset(skip).limit(limit)
    
    # Execute
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()
    
    result = await db.execute(stmt)
    companies = list(result.scalars().all())
    
    return companies, total

async def delete_company(db: AsyncSession, workspace_id: UUID, company_id: UUID) -> None:
    company = await get_company(db, workspace_id, company_id)
    if company:
        await db.delete(company)

# For unlink use
async def get_company_for_update(db: AsyncSession, workspace_id: UUID, company_id: UUID) -> Company | None:
    stmt = select(Company).where(
        Company.workspace_id == workspace_id,
        Company.id == company_id
    ).with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
