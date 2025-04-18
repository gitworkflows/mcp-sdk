from typing import Optional
import uvicorn
from fastapi import FastAPI
from ..server import ServerConfig

class ServerRunner:
    """Runner for MCP server with uvicorn configuration"""

    def __init__(
        self,
        app: FastAPI,
        config: Optional[ServerConfig] = None
    ):
        """
        Initialize the server runner.

        Args:
            app: FastAPI application instance
            config: Server configuration
        """
        self.app = app
        self.config = config or ServerConfig()

    def run(self):
        """Run the server with uvicorn"""
        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port,
            debug=self.config.debug,
            workers=self.config.workers,
            ssl_keyfile=self.config.ssl_keyfile,
            ssl_certfile=self.config.ssl_certfile,
            log_level="info",
            access_log=True,
            proxy_headers=True,
            server_header=True,
            date_header=True
        ) 