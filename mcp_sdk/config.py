import os
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator

class MCPConfig(BaseModel):
    """MCP Configuration Model"""
    api_key: str
    endpoint: str
    timeout: int = Field(default=30, gt=0)
    max_retries: int = Field(default=3, ge=0)
    retry_backoff_factor: float = Field(default=0.5, ge=0.0)
    verify_ssl: bool = Field(default=True)
    proxy: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator('endpoint')
    def validate_endpoint(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('endpoint must start with http:// or https://')
        return v.rstrip('/')

class ConfigManager:
    """Manages MCP configuration loading and validation"""

    DEFAULT_CONFIG_PATHS = [
        Path('mcp_config.json'),
        Path('mcp_config.yaml'),
        Path('~/.mcp/config.json').expanduser(),
        Path('~/.mcp/config.yaml').expanduser()
    ]

    @classmethod
    def load_config(cls, config_path: Optional[str] = None) -> MCPConfig:
        """
        Load configuration from file or environment.

        Args:
            config_path: Optional path to config file

        Returns:
            MCPConfig: Loaded configuration

        Raises:
            ValueError: If configuration is invalid or not found
        """
        # Try to load from provided path
        if config_path:
            config_file = Path(config_path)
            if config_file.exists():
                return cls._load_config_file(config_file)

        # Try default paths
        for path in cls.DEFAULT_CONFIG_PATHS:
            if path.exists():
                return cls._load_config_file(path)

        # Try environment variables
        env_config = cls._load_env_config()
        if env_config:
            return env_config

        raise ValueError(
            "No configuration found. Please provide a config file or set environment variables."
        )

    @classmethod
    def _load_config_file(cls, path: Path) -> MCPConfig:
        """Load configuration from file"""
        try:
            with open(path) as f:
                if path.suffix == '.json':
                    config_data = json.load(f)
                else:
                    config_data = yaml.safe_load(f)
                return MCPConfig(**config_data)
        except Exception as e:
            raise ValueError(f"Error loading config file {path}: {str(e)}")

    @classmethod
    def _load_env_config(cls) -> Optional[MCPConfig]:
        """Load configuration from environment variables"""
        env_vars = {
            'api_key': os.getenv('MCP_API_KEY'),
            'endpoint': os.getenv('MCP_ENDPOINT'),
            'timeout': os.getenv('MCP_TIMEOUT'),
            'max_retries': os.getenv('MCP_MAX_RETRIES'),
            'retry_backoff_factor': os.getenv('MCP_RETRY_BACKOFF_FACTOR'),
            'verify_ssl': os.getenv('MCP_VERIFY_SSL'),
        }

        # Filter out None values and convert types
        config_data = {}
        for key, value in env_vars.items():
            if value is not None:
                if key in ['timeout', 'max_retries']:
                    config_data[key] = int(value)
                elif key == 'retry_backoff_factor':
                    config_data[key] = float(value)
                elif key == 'verify_ssl':
                    config_data[key] = value.lower() == 'true'
                else:
                    config_data[key] = value

        if not config_data.get('api_key') or not config_data.get('endpoint'):
            return None

        return MCPConfig(**config_data) 