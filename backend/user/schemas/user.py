from enum import Enum
from pydantic import BaseModel, EmailStr, Field
from typing import List


class Role(str, Enum):
    admin = "admin",
    user = "user",
    manager = "manager"


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=6)


class UserSchema(BaseModel):
    id: str
    username: str
    email: EmailStr
    is_active: bool = True
    roles: List[Role] = [Role.user]
