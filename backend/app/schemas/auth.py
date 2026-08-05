from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)
