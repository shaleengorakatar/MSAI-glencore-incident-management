"""
User models for role-based access control.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    WORKER = "worker"
    MANAGER = "manager"


class User(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    site: Optional[str] = None  # Worker's assigned site


class UserLogin(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    site: Optional[str] = None


# Mock user database (in production, use real database)
MOCK_USERS = {
    "worker@client.com": {
        "id": "user-1",
        "email": "worker@client.com",
        "name": "John Worker",
        "role": UserRole.WORKER,
        "site": "Elkview Operations - Sparwood, BC",
        "password": "worker123"  # In production, hash this!
    },
    "manager@client.com": {
        "id": "user-2", 
        "email": "manager@client.com",
        "name": "Sarah Manager",
        "role": UserRole.MANAGER,
        "site": None,
        "password": "manager123"  # In production, hash this!
    },
    "sudbury.worker@client.com": {
        "id": "user-3",
        "email": "sudbury.worker@client.com", 
        "name": "Mike Worker",
        "role": UserRole.WORKER,
        "site": "Sudbury Integrated Nickel Operations - Sudbury, Ontario",
        "password": "worker123"
    },
    "chile.manager@client.com": {
        "id": "user-4",
        "email": "chile.manager@client.com",
        "name": "Carlos Manager", 
        "role": UserRole.MANAGER,
        "site": None,
        "password": "manager123"
    }
}
