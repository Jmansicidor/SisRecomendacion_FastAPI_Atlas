from enum import Enum
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List


class Role(str, Enum):
    admin = "admin"
    user = "user"
    manager = "manager"


class User(BaseModel):
    __tablename__ = 'user'

    id: Optional[str] = None
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password_hash: str
    is_active: bool = True
    roles: List[Role] = [Role.user]
