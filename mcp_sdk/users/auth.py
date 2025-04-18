from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from .models import Session, User, TokenRefreshRequest, TokenRefreshResponse

# These would typically be loaded from environment variables or configuration
JWT_SECRET = "your-secret-key"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: The data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: The data to encode in the token

    Returns:
        str: The encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify a JWT token.

    Args:
        token: The token to verify

    Returns:
        Dict[str, Any]: The decoded token data

    Raises:
        jwt.PyJWTError: If the token is invalid
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

def authenticate(username: str, password: str) -> Optional[Session]:
    """
    Authenticate a user and create a session.

    Args:
        username: The username
        password: The password

    Returns:
        Optional[Session]: The created session if authentication is successful
    """
    # This would typically verify against a database
    # For now, we'll use a simple mock
    if username == "admin" and password == "admin":
        user_data = {
            "id": "1",
            "username": username,
            "role": "admin"
        }
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)
        
        return Session(
            id="1",
            user_id="1",
            token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
    return None

def refresh_token(refresh_token: str) -> Optional[TokenRefreshResponse]:
    """
    Refresh an access token using a refresh token.

    Args:
        refresh_token: The refresh token

    Returns:
        Optional[TokenRefreshResponse]: The new token information if refresh is successful
    """
    try:
        payload = verify_token(refresh_token)
        access_token = create_access_token(payload)
        new_refresh_token = create_refresh_token(payload)
        
        return TokenRefreshResponse(
            token=access_token,
            refresh_token=new_refresh_token,
            expires_at=datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
    except jwt.PyJWTError:
        return None

def logout(session_id: str) -> bool:
    """
    Invalidate a session.

    Args:
        session_id: The ID of the session to invalidate

    Returns:
        bool: True if the session was invalidated successfully
    """
    # This would typically remove the session from a database
    # For now, we'll just return True
    return True

def validate_session(session_id: str) -> bool:
    """
    Validate a session.

    Args:
        session_id: The ID of the session to validate

    Returns:
        bool: True if the session is valid
    """
    # This would typically check the session in a database
    # For now, we'll just return True
    return True 