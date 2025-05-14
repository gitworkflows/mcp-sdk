from typing import Optional, Dict, Any, List, TypeVar, Generic, Type, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator

# Type variables for resource handling
T = TypeVar("T", bound=BaseModel)
R = TypeVar("R", bound=BaseModel)


class ResourceMetadata(BaseModel):
    """Standardized metadata for resources"""

    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: str
    status: str
    tags: List[str] = Field(default_factory=list)
    custom_data: Optional[Dict[str, Any]] = None


class ResourceLinks(BaseModel):
    """Standardized links for resources"""

    self: str
    parent: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    related: List[str] = Field(default_factory=list)


class ResourceResponse(BaseModel, Generic[R]):
    """Standardized response format for resources"""

    data: R
    metadata: ResourceMetadata
    links: ResourceLinks
    included: Optional[List[Dict[str, Any]]] = None


class PaginationInfo(BaseModel):
    """Standardized pagination information"""

    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool
    next_page: Optional[str] = None
    prev_page: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[R]):
    """Standardized paginated response format"""

    data: List[R]
    metadata: List[ResourceMetadata]
    links: ResourceLinks
    pagination: PaginationInfo
    included: Optional[List[Dict[str, Any]]] = None


class ResourceError(BaseModel):
    """Standardized error format for resources"""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    field: Optional[str] = None


class ResourceErrorResponse(BaseModel):
    """Standardized error response format"""

    errors: List[ResourceError]
    metadata: ResourceMetadata
    links: ResourceLinks


class ResourceFilter(BaseModel):
    """Standardized filter format for resources"""

    field: str
    operator: str
    value: Any


class ResourceQuery(BaseModel):
    """Standardized query format for resources"""

    filters: List[ResourceFilter] = Field(default_factory=list)
    sort: List[str] = Field(default_factory=list)
    include: List[str] = Field(default_factory=list)
    page: Optional[int] = None
    per_page: Optional[int] = None


class ResourceCreate(BaseModel, Generic[T]):
    """Standardized create format for resources"""

    data: T
    metadata: Optional[Dict[str, Any]] = None


class ResourceUpdate(BaseModel, Generic[T]):
    """Standardized update format for resources"""

    data: T
    metadata: Optional[Dict[str, Any]] = None


class ResourceDelete(BaseModel):
    """Standardized delete format for resources"""

    force: bool = False
    reason: Optional[str] = None
