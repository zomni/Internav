from uuid import UUID

from pydantic import BaseModel


class UserCreateRequest(BaseModel):
    email: str
    password: str
    role: str
    organization_id: UUID | None = None


class UserUpdateRoleRequest(BaseModel):
    role: str


class UserUpdatePasswordRequest(BaseModel):
    new_password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    organization_id: UUID | None
    is_active: bool
    created_at: str
    updated_at: str
