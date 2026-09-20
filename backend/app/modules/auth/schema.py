from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    user: UserResponse | None = None

class MessageResponse(BaseModel):
    message: str

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str
