from typing import Optional, Dict, Any, List
from datetime import datetime
import requests
from ...client import MCPClient
from .models import (
    User,
    Session,
    UserCreate,
    UserUpdate,
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    TokenRefreshResponse
)

class UserClient:
    """Client for user management operations"""

    def __init__(self, base_client: MCPClient):
        """
        Initialize the user client.

        Args:
            base_client: An instance of MCPClient
        """
        self.client = base_client
        self._current_session: Optional[Session] = None

    @property
    def current_session(self) -> Optional[Session]:
        """Get the current active session"""
        return self._current_session

    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            User: The created user
        """
        response = self.client.send({
            "operation": "create_user",
            "data": user_data.dict()
        })
        return User(**response)

    def update_user(self, user_id: str, user_data: UserUpdate) -> User:
        """
        Update an existing user.

        Args:
            user_id: The ID of the user to update
            user_data: User update data

        Returns:
            User: The updated user
        """
        response = self.client.send({
            "operation": "update_user",
            "user_id": user_id,
            "data": user_data.dict(exclude_unset=True)
        })
        return User(**response)

    def get_user(self, user_id: str) -> User:
        """
        Get a user by ID.

        Args:
            user_id: The ID of the user to retrieve

        Returns:
            User: The requested user
        """
        response = self.client.send({
            "operation": "get_user",
            "user_id": user_id
        })
        return User(**response)

    def list_users(self, **filters) -> List[User]:
        """
        List users with optional filtering.

        Args:
            **filters: Filter parameters

        Returns:
            List[User]: List of users matching the filters
        """
        response = self.client.send({
            "operation": "list_users",
            "filters": filters
        })
        return [User(**user_data) for user_data in response]

    def delete_user(self, user_id: str) -> None:
        """
        Delete a user.

        Args:
            user_id: The ID of the user to delete
        """
        self.client.send({
            "operation": "delete_user",
            "user_id": user_id
        })

    def login(self, username: str, password: str, remember_me: bool = False) -> LoginResponse:
        """
        Login a user and create a session.

        Args:
            username: The username
            password: The password
            remember_me: Whether to create a long-lived session

        Returns:
            LoginResponse: The login response containing user and session
        """
        request = LoginRequest(
            username=username,
            password=password,
            remember_me=remember_me
        )
        response = self.client.send({
            "operation": "login",
            "data": request.dict()
        })
        login_response = LoginResponse(**response)
        self._current_session = login_response.session
        return login_response

    def logout(self) -> None:
        """Logout the current user and invalidate the session"""
        if self._current_session:
            self.client.send({
                "operation": "logout",
                "session_id": self._current_session.id
            })
            self._current_session = None

    def refresh_token(self) -> TokenRefreshResponse:
        """
        Refresh the current session token.

        Returns:
            TokenRefreshResponse: The new token information
        """
        if not self._current_session:
            raise ValueError("No active session to refresh")

        request = TokenRefreshRequest(
            refresh_token=self._current_session.refresh_token
        )
        response = self.client.send({
            "operation": "refresh_token",
            "data": request.dict()
        })
        refresh_response = TokenRefreshResponse(**response)
        
        # Update current session with new token
        self._current_session.token = refresh_response.token
        self._current_session.refresh_token = refresh_response.refresh_token
        self._current_session.expires_at = refresh_response.expires_at
        
        return refresh_response

    def validate_session(self) -> bool:
        """
        Validate the current session.

        Returns:
            bool: True if the session is valid, False otherwise
        """
        if not self._current_session:
            return False

        try:
            self.client.send({
                "operation": "validate_session",
                "session_id": self._current_session.id
            })
            return True
        except:
            return False 