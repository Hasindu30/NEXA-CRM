from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, StringConstraints
from typing import Annotated

class WorkspaceCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class WorkspaceListResponse(BaseModel):
    data: list[WorkspaceResponse]

class WorkspaceMemberResponse(BaseModel):
    user_id: UUID
    email: str
    role: str
    joined_at: datetime
    
class WorkspaceMemberListResponse(BaseModel):
    data: list[WorkspaceMemberResponse]

class AddWorkspaceMemberRequest(BaseModel):
    email: str

class ChangeWorkspaceMemberRoleRequest(BaseModel):
    role: str
