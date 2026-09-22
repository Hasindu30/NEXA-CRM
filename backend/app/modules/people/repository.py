from uuid import UUID
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.people.model import Person
from app.modules.companies.model import Company

async def create_person(db: AsyncSession, person: Person) -> Person:
    db.add(person)
    return person

async def get_person(db: AsyncSession, workspace_id: UUID, person_id: UUID) -> tuple[Person, Company | None] | None:
    stmt = select(Person, Company).outerjoin(
        Company, 
        (Person.company_id == Company.id) & (Company.workspace_id == workspace_id)
    ).where(
        Person.workspace_id == workspace_id,
        Person.id == person_id
    )
    result = await db.execute(stmt)
    return result.first()

async def list_people(
    db: AsyncSession, 
    workspace_id: UUID, 
    q: str | None = None, 
    skip: int = 0, 
    limit: int = 50
) -> tuple[list[tuple[Person, Company | None]], int]:
    
    # Base query for data
    stmt = select(Person, Company).outerjoin(
        Company,
        (Person.company_id == Company.id) & (Company.workspace_id == workspace_id)
    ).where(Person.workspace_id == workspace_id)
    
    # Base query for count
    count_stmt = select(func.count()).select_from(Person).where(Person.workspace_id == workspace_id)
    
    if q:
        q = q.strip()
        if q:
            search_filter = or_(
                Person.first_name.ilike(f"%{q}%"),
                Person.last_name.ilike(f"%{q}%"),
                Person.email.ilike(f"%{q}%")
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)
            
    stmt = stmt.order_by(Person.created_at.desc(), Person.id.desc())
    stmt = stmt.offset(skip).limit(limit)
    
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()
    
    result = await db.execute(stmt)
    people = list(result.all())
    
    return people, total

async def delete_person(db: AsyncSession, workspace_id: UUID, person_id: UUID) -> None:
    stmt = select(Person).where(
        Person.workspace_id == workspace_id,
        Person.id == person_id
    )
    result = await db.execute(stmt)
    person = result.scalar_one_or_none()
    if person:
        await db.delete(person)

async def unlink_people_from_company(db: AsyncSession, workspace_id: UUID, company_id: UUID) -> None:
    stmt = select(Person).where(
        Person.workspace_id == workspace_id,
        Person.company_id == company_id
    )
    result = await db.execute(stmt)
    people = result.scalars().all()
    for p in people:
        p.company_id = None
