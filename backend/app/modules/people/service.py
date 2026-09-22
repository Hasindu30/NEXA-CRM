from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.modules.people.model import Person
from app.modules.people.schema import PersonCreate, PersonUpdate, PaginatedPersonResponse, PersonResponse, CompanySummary
from app.modules.people import repository
from app.modules.companies.repository import get_company

def _map_to_response(person: Person, company) -> dict:
    comp_summary = None
    if company:
        comp_summary = CompanySummary(id=company.id, name=company.name)
        
    return {
        "id": person.id,
        "workspace_id": person.workspace_id,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "email": person.email,
        "phone": person.phone,
        "job_title": person.job_title,
        "company_id": person.company_id,
        "company": comp_summary,
        "created_at": person.created_at,
        "updated_at": person.updated_at
    }

async def create_person(db: AsyncSession, workspace_id: UUID, data: PersonCreate) -> dict:
    if data.company_id:
        company = await get_company(db, workspace_id, data.company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found in this workspace")
            
    person = Person(
        workspace_id=workspace_id,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        job_title=data.job_title,
        company_id=data.company_id
    )
    
    await repository.create_person(db, person)
    await db.commit()
    await db.refresh(person)
    
    company = None
    if person.company_id:
        company = await get_company(db, workspace_id, person.company_id)
        
    return _map_to_response(person, company)

async def get_person(db: AsyncSession, workspace_id: UUID, person_id: UUID) -> dict:
    result = await repository.get_person(db, workspace_id, person_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
        
    person, company = result
    return _map_to_response(person, company)

async def list_people(
    db: AsyncSession, 
    workspace_id: UUID, 
    q: str | None, 
    page: int, 
    limit: int
) -> PaginatedPersonResponse:
    skip = (page - 1) * limit
    results, total = await repository.list_people(db, workspace_id, q, skip, limit)
    
    mapped_data = [_map_to_response(p, c) for p, c in results]
    
    return PaginatedPersonResponse(
        data=mapped_data, # type: ignore
        meta={
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 1
        }
    )

async def update_person(db: AsyncSession, workspace_id: UUID, person_id: UUID, data: PersonUpdate) -> dict:
    result = await repository.get_person(db, workspace_id, person_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
        
    person, _ = result
    
    update_data = data.model_dump(exclude_unset=True)
    
    if "company_id" in update_data and update_data["company_id"] is not None:
        company = await get_company(db, workspace_id, update_data["company_id"])
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found in this workspace")
            
    for key, value in update_data.items():
        setattr(person, key, value)
        
    has_first_name = bool(person.first_name and person.first_name.strip())
    has_last_name = bool(person.last_name and person.last_name.strip())
    has_email = bool(person.email and person.email.strip())
    
    if not (has_first_name or has_last_name or has_email):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one identity field (first_name, last_name, or email) is required")
        
    await db.commit()
    await db.refresh(person)
    
    company = None
    if person.company_id:
        company = await get_company(db, workspace_id, person.company_id)
        
    return _map_to_response(person, company)

async def delete_person(db: AsyncSession, workspace_id: UUID, person_id: UUID) -> None:
    result = await repository.get_person(db, workspace_id, person_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
        
    await repository.delete_person(db, workspace_id, person_id)
    await db.commit()
