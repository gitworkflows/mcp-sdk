from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

class UserRole(str):
    """User role enumeration"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class User(BaseModel):
    """User model"""
    id: str
    username: str
    email: EmailStr
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None

class Session(BaseModel):
    """Session model"""
    id: str
    user_id: str
    token: str
    refresh_token: str
    expires_at: datetime
    created_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class UserCreate(BaseModel):
    """User creation model"""
    username: str
    email: EmailStr
    password: str
    role: UserRole = Field(default=UserRole.USER)
    metadata: Optional[Dict[str, Any]] = None

class UserUpdate(BaseModel):
    """User update model"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str
    remember_me: bool = False

class LoginResponse(BaseModel):
    """Login response model"""
    user: User
    session: Session

class TokenRefreshRequest(BaseModel):
    """Token refresh request model"""
    refresh_token: str

class TokenRefreshResponse(BaseModel):
    """Token refresh response model"""
    token: str
    refresh_token: str
    expires_at: datetime 