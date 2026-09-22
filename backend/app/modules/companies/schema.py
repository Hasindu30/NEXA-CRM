from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator
from typing import Annotated, Optional

class CompanyCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    domain: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] | None = None
    website: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None

class CompanyUpdate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)] | None = None
    domain: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] | None = None
    website: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None

    @field_validator("name")
    def name_cannot_be_none(cls, v):
        if v is None:
            raise ValueError("Company name cannot be null")
        return v

class CompanyResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    domain: str | None
    phone: str | None
    website: str | None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PaginationMeta(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int

class PaginatedCompanyResponse(BaseModel):
    data: list[CompanyResponse]
    meta: PaginationMeta
