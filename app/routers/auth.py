"""
Authentication router for login and user management.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from passlib.context import CryptContext

from app.config import settings
from app.models.user import User, UserLogin, UserResponse, UserRole, MOCK_USERS

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Settings (use environment variables in production)
JWT_SECRET = settings.openai_api_key or "fallback-secret-change-in-production"  # Reuse API key as secret
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


def create_access_token(data: Dict) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    to_encode.update({
        "exp": datetime.now(timezone.utc).timestamp() + (JWT_EXPIRATION_HOURS * 3600)
    })
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials) -> User:
    """Verify JWT token and return user."""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if email is None or email not in MOCK_USERS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        user_data = MOCK_USERS[email]
        return User(**user_data)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


def get_current_user(credentials: HTTPAuthorizationCredentials = security) -> User:
    """Dependency to get current authenticated user."""
    return verify_token(credentials)


@router.post("/login", response_model=UserResponse)
async def login(login_data: UserLogin):
    """Authenticate user and return JWT token."""
    email = login_data.email
    password = login_data.password
    
    # Find user in mock database
    if email not in MOCK_USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    user_data = MOCK_USERS[email]
    
    # Verify password (in production, use proper hashing)
    if user_data["password"] != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create access token
    access_token = create_access_token({"sub": email})
    
    # Return user info (without password)
    user_response = UserResponse(**{k: v for k, v in user_data.items() if k != "password"})
    
    # Add token to response headers
    return user_response


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = get_current_user):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        site=current_user.site
    )


@router.post("/logout")
async def logout():
    """Logout endpoint (client-side token removal)."""
    return {"message": "Successfully logged out"}
