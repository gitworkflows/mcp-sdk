from typing import Optional, List
from pydantic import BaseModel


class ServerConfig(BaseModel):
    """Server configuration model"""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    workers: int = 1
    ssl_keyfile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    cors_origins: List[str] = ["*"]
    cors_methods: List[str] = ["*"]
    cors_headers: List[str] = ["*"]
