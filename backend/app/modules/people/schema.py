from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator
from typing import Annotated

from app.modules.companies.schema import CompanyResponse

class CompanySummary(BaseModel):
    id: UUID
    name: str

class PersonCreate(BaseModel):
    first_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    last_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] | None = None
    job_title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    company_id: UUID | None = None

    @model_validator(mode='after')
    def check_identity(self) -> 'PersonCreate':
        has_first_name = bool(self.first_name and self.first_name.strip())
        has_last_name = bool(self.last_name and self.last_name.strip())
        has_email = bool(self.email and self.email.strip())
        if not (has_first_name or has_last_name or has_email):
            raise ValueError("At least one identity field (first_name, last_name, or email) is required")
        return self

class PersonUpdate(BaseModel):
    first_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    last_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] | None = None
    job_title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    company_id: UUID | None = None

    # We do NOT run check_identity here because PATCH is partial. The service layer will validate the merged result.

class PersonResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    first_name: str | None
    last_name: str | None
    email: str | None
    phone: str | None
    job_title: str | None
    company_id: UUID | None
    company: CompanySummary | None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PaginationMeta(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int

class PaginatedPersonResponse(BaseModel):
    data: list[PersonResponse]
    meta: PaginationMeta
