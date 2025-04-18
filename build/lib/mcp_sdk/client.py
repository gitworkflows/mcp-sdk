from typing import Optional, Dict, Any, List, TypeVar, Generic, Type, Union
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
from pydantic import BaseModel, Field, validator

from .models import MCPRequest, MCPResponse, ClientInfo, ClientConfig, Commit, CommitResponse, ServerOptions, CommitRequest
from .resources import (
    ResourceResponse,
    PaginatedResponse,
    ResourceErrorResponse,
    ResourceQuery,
    ResourceCreate,
    ResourceUpdate,
    ResourceDelete
)
from .exceptions import (
    MCPError,
    MCPConnectionError,
    MCPAuthenticationError,
    MCPValidationError,
    MCPRateLimitError,
    MCPTimeoutError,
    MCPResourceNotFoundError,
    MCPPermissionError,
    MCPConfigurationError
)

# Type variables for generic request/response handling
T = TypeVar('T', bound=BaseModel)
R = TypeVar('R', bound=BaseModel)

class RequestOptions(BaseModel):
    """Options for API requests"""
    timeout: int = Field(default=30, gt=0)
    retry_count: int = Field(default=3, ge=0)
    retry_backoff_factor: float = Field(default=0.5, ge=0.0)
    retry_status_codes: List[int] = Field(
        default_factory=lambda: [500, 502, 503, 504, 408, 429]
    )
    retry_methods: List[str] = Field(
        default_factory=lambda: ['HEAD', 'GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'TRACE']
    )
    headers: Dict[str, str] = Field(default_factory=dict)
    verify_ssl: bool = Field(default=True)

class ResponseMetadata(BaseModel):
    """Metadata for API responses"""
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status_code: int
    headers: Dict[str, str]
    elapsed: float

class TypedResponse(BaseModel, Generic[R]):
    """Typed response wrapper"""
    data: R
    metadata: ResponseMetadata

class MCPClient:
    """Client for interacting with the MCP API"""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        client_info: Optional[ClientInfo] = None,
        config: Optional[ClientConfig] = None,
        options: Optional[RequestOptions] = None
    ):
        """
        Initialize the MCP client.

        Args:
            api_key: Your MCP API key
            endpoint: The MCP API endpoint
            client_info: Client information
            config: Client configuration
            options: Request options

        Raises:
            MCPConfigurationError: If the configuration is invalid
        """
        if not api_key:
            raise MCPConfigurationError("API key is required", setting="api_key")
        if not endpoint:
            raise MCPConfigurationError("Endpoint is required", setting="endpoint")
            
        self.api_key = api_key
        self.endpoint = endpoint.rstrip('/')
        self.client_info = client_info or self._create_default_client_info()
        self.config = config or ClientConfig(
            api_key=api_key,
            endpoint=endpoint
        )
        self.options = options or RequestOptions()
        
        self.session = self._create_session()

    def _create_default_client_info(self) -> ClientInfo:
        """Create default client information"""
        return ClientInfo(
            name="mcp-python-client",
            version="0.1.0",
            platform="python",
            environment="production",
            language="python",
            language_version="3.8",
            sdk_version="0.1.0"
        )

    def _create_session(self) -> requests.Session:
        """Create a requests session with enhanced retry logic"""
        try:
            session = requests.Session()
            
            retry_strategy = Retry(
                total=self.options.retry_count,
                backoff_factor=self.options.retry_backoff_factor,
                status_forcelist=self.options.retry_status_codes,
                allowed_methods=self.options.retry_methods,
                jitter=0.1,
                respect_retry_after_header=True,
                raise_on_status=True
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            return session
        except Exception as e:
            raise MCPConfigurationError(f"Failed to create session: {str(e)}") from e

    def _prepare_headers(self) -> Dict[str, str]:
        """Prepare headers for API requests"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Client-Name": self.client_info.name,
            "X-Client-Version": self.client_info.version,
            "X-Client-Platform": self.client_info.platform
        }
        headers.update(self.options.headers)
        return headers

    def _handle_response(
        self,
        response: requests.Response,
        response_type: Type[R]
    ) -> Union[ResourceResponse[R], PaginatedResponse[R], ResourceErrorResponse]:
        """Handle API response and return standardized resource response"""
        try:
            response.raise_for_status()
            response_data = response.json()
            
            # Check if it's a paginated response
            if isinstance(response_data, dict) and 'pagination' in response_data:
                return PaginatedResponse[R](**response_data)
            
            # Check if it's a single resource response
            if isinstance(response_data, dict) and 'data' in response_data:
                return ResourceResponse[R](**response_data)
            
            # Handle error response
            if isinstance(response_data, dict) and 'errors' in response_data:
                return ResourceErrorResponse(**response_data)
            
            # Handle raw response
            return ResourceResponse[R](
                data=response_type(**response_data),
                metadata=ResourceMetadata(
                    id=str(response.headers.get("X-Request-ID", "")),
                    version="1.0",
                    status="success"
                ),
                links=ResourceLinks(
                    self=response.url
                )
            )
            
        except requests.exceptions.RequestException as e:
            error_response = None
            try:
                error_response = response.json()
            except:
                pass

            if isinstance(e, requests.exceptions.ConnectionError):
                raise MCPConnectionError(
                    "Failed to connect to MCP API",
                    status_code=response.status_code,
                    response=error_response
                ) from e
            elif isinstance(e, requests.exceptions.Timeout):
                raise MCPTimeoutError(
                    "Request timed out",
                    timeout=self.options.timeout,
                    status_code=response.status_code,
                    response=error_response
                ) from e
            elif response.status_code == 401:
                raise MCPAuthenticationError(
                    "Invalid API key",
                    status_code=response.status_code,
                    response=error_response
                ) from e
            elif response.status_code == 403:
                raise MCPPermissionError(
                    "Permission denied",
                    status_code=response.status_code,
                    response=error_response
                ) from e
            elif response.status_code == 404:
                raise MCPResourceNotFoundError(
                    "Resource not found",
                    status_code=response.status_code,
                    response=error_response
                ) from e
            elif response.status_code == 422:
                raise MCPValidationError(
                    "Invalid request parameters",
                    validation_errors=error_response,
                    status_code=response.status_code,
                    response=error_response
                ) from e
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                raise MCPRateLimitError(
                    "Rate limit exceeded",
                    retry_after=int(retry_after) if retry_after else None,
                    status_code=response.status_code,
                    response=error_response
                ) from e
            else:
                raise MCPError(
                    f"API request failed: {str(e)}",
                    status_code=response.status_code,
                    response=error_response
                ) from e

    async def send(
        self,
        request: MCPRequest,
        response_type: Type[R] = MCPResponse
    ) -> Union[ResourceResponse[R], PaginatedResponse[R], ResourceErrorResponse]:
        """
        Send a request to the MCP API.

        Args:
            request: The MCP request
            response_type: Expected response type

        Returns:
            Union[ResourceResponse[R], PaginatedResponse[R], ResourceErrorResponse]: The standardized API response

        Raises:
            MCPError: If the request fails
            MCPValidationError: If the request data is invalid
        """
        try:
            # Prepare request data
            request_data = request.dict()
            request_data["client_info"] = self.client_info.dict()

            # Make the request
            response = self.session.post(
                f"{self.endpoint}/api/v1/process",
                json=request_data,
                headers=self._prepare_headers(),
                timeout=self.options.timeout,
                verify=self.options.verify_ssl
            )

            # Handle response
            return self._handle_response(response, response_type)

        except Exception as e:
            if not isinstance(e, MCPError):
                raise MCPError(f"Unexpected error: {str(e)}") from e
            raise

    def close(self):
        """Close the client session"""
        try:
            self.session.close()
        except Exception as e:
            raise MCPError(f"Failed to close session: {str(e)}") from e

    async def get_commit(
        self,
        sha: str,
        options: Optional[ServerOptions] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ResourceResponse[Commit]:
        """
        Get a single commit with configurable options.

        Args:
            sha: The commit SHA
            options: Server options to control what data is included in the response
            metadata: Additional metadata to include with the request

        Returns:
            ResourceResponse[Commit]: The commit data with metadata

        Raises:
            MCPError: If the request fails
            MCPResourceNotFoundError: If the commit is not found
        """
        try:
            # Prepare request data
            request = CommitRequest(
                sha=sha,
                options=options,
                metadata=metadata
            )

            # Make the request
            response = self.session.get(
                f"{self.endpoint}/api/v1/commits/{sha}",
                json=request.dict(),
                headers=self._prepare_headers(),
                timeout=self.options.timeout,
                verify=self.options.verify_ssl
            )

            # Handle response
            return self._handle_response(response, Commit)

        except MCPResourceNotFoundError:
            raise MCPResourceNotFoundError(f"Commit {sha} not found")
        except Exception as e:
            if not isinstance(e, MCPError):
                raise MCPError(f"Failed to get commit: {str(e)}") from e
            raise 