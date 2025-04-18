from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from datetime import datetime

class MCPSettings(BaseModel):
    """Settings for MCP requests"""
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=150, gt=0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)

class MCPRequest(BaseModel):
    """MCP API request model"""
    model: str
    context: str
    settings: MCPSettings
    metadata: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    """MCP API response model"""
    id: str
    model: str
    content: str
    created_at: str
    usage: Dict[str, int]
    metadata: Optional[Dict[str, Any]] = None

class ClientInfo(BaseModel):
    """Client information model"""
    name: str
    version: str
    platform: str
    environment: str = Field(default="production")
    language: str = Field(default="python")
    language_version: str
    sdk_version: str
    client_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ClientConfig(BaseModel):
    """Client configuration model"""
    api_key: str
    endpoint: str
    timeout: int = Field(default=30)
    max_retries: int = Field(default=3)
    retry_backoff_factor: float = Field(default=0.5)
    verify_ssl: bool = Field(default=True)
    proxy: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None

class CommitFile(BaseModel):
    """Model for a file in a commit"""
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None
    raw_url: Optional[str] = None
    blob_url: Optional[str] = None

class CommitStats(BaseModel):
    """Model for commit statistics"""
    total: int
    additions: int
    deletions: int
    files: List[CommitFile]

class CommitAuthor(BaseModel):
    """Model for commit author information"""
    name: str
    email: str
    date: datetime
    username: Optional[str] = None

class Commit(BaseModel):
    """Model for a commit"""
    sha: str
    message: str
    author: CommitAuthor
    committer: CommitAuthor
    url: str
    html_url: str
    stats: CommitStats
    files: List[CommitFile]
    parents: List[str]
    verification: Optional[Dict[str, Any]] = None
    node_id: Optional[str] = None
    tree: Optional[Dict[str, str]] = None
    comments_url: Optional[str] = None
    commit_url: Optional[str] = None

class CommitResponse(BaseModel):
    """Model for commit API response"""
    data: Commit
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ServerOptions(BaseModel):
    """Options that can be passed through to the server"""
    include_raw: bool = Field(default=False, description="Include raw data in response")
    include_verification: bool = Field(default=True, description="Include commit verification data")
    include_tree: bool = Field(default=False, description="Include tree data")
    include_comments: bool = Field(default=False, description="Include comments data")
    include_parents: bool = Field(default=True, description="Include parent commits")
    include_stats: bool = Field(default=True, description="Include commit statistics")
    include_files: bool = Field(default=True, description="Include file changes")
    custom_options: Optional[Dict[str, Any]] = Field(default=None, description="Additional custom options")

class CommitRequest(BaseModel):
    """Request model for getting a commit"""
    sha: str
    options: Optional[ServerOptions] = None
    metadata: Optional[Dict[str, Any]] = None 