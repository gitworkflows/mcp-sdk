from typing import Optional
import uvicorn
from fastapi import FastAPI
from mcp_sdk.server_config import ServerConfig

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
        kwargs = {
            'host': self.config.host,
            'port': self.config.port,
            'log_level': "debug" if self.config.debug else "info",
            'access_log': True,
            'proxy_headers': True,
            'server_header': True,
            'date_header': True
        }

        # Add SSL configuration if provided
        if self.config.ssl_keyfile and self.config.ssl_certfile:
            kwargs['ssl_keyfile'] = self.config.ssl_keyfile
            kwargs['ssl_certfile'] = self.config.ssl_certfile

        if self.config.debug:
            # In debug mode, we need to pass the app as an import string
            # For now, we'll disable reload in debug mode since we can't reliably get the module path
            kwargs['reload'] = False
            kwargs['app'] = self.app
        else:
            # In production, we can pass the app directly
            kwargs['app'] = self.app
            kwargs['workers'] = self.config.workers

        uvicorn.run(**kwargs)