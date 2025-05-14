import pytest
import os
import tempfile
import json
import yaml
from pathlib import Path
from mcp_sdk.config import MCPConfig, ConfigManager

class TestConfig:
    """Tests for configuration management."""
    
    @pytest.fixture
    def sample_config_data(self):
        return {
            "api_key": "test-key",
            "endpoint": "https://api.example.com",
            "timeout": 60,
            "max_retries": 5,
            "retry_backoff_factor": 1.0,
            "verify_ssl": True
        }
    
    def test_config_validation(self, sample_config_data):
        """Test configuration validation."""
        config = MCPConfig(**sample_config_data)
        assert config.api_key == "test-key"
        assert config.endpoint == "https://api.example.com"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_backoff_factor == 1.0
        assert config.verify_ssl is True
        
    def test_config_defaults(self):
        """Test configuration defaults."""
        config = MCPConfig(
            api_key="test-key",
            endpoint="https://api.example.com"
        )
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_backoff_factor == 0.5
        assert config.verify_ssl is True
        assert config.proxy is None
        assert config.headers is None
        assert config.metadata is None
        
    def test_config_endpoint_validation(self):
        """Test endpoint URL validation."""
        # Test valid HTTPS URL
        config = MCPConfig(
            api_key="test-key",
            endpoint="https://api.example.com"
        )
        assert config.endpoint == "https://api.example.com"
        
        # Test valid HTTP URL
        config = MCPConfig(
            api_key="test-key",
            endpoint="http://localhost:8000"
        )
        assert config.endpoint == "http://localhost:8000"
        
        # Test invalid URL
        with pytest.raises(ValueError, match="endpoint must start with http:// or https://"):
            MCPConfig(
                api_key="test-key",
                endpoint="invalid-url"
            )
    
    def test_endpoint_trailing_slash_handling(self):
        """Test handling of trailing slashes in endpoints."""
        config = MCPConfig(
            api_key="test-key",
            endpoint="https://api.example.com/"
        )
        assert config.endpoint == "https://api.example.com"

    @pytest.fixture
    def temp_config_file(self, sample_config_data):
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config_data, f)
            path = f.name
        
        yield path
        
        # Cleanup
        os.unlink(path)

    @pytest.fixture
    def temp_yaml_config_file(self, sample_config_data):
        """Create a temporary YAML config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config_data, f)
            path = f.name
        
        yield path
        
        # Cleanup
        os.unlink(path)

    def test_load_config_file_json(self, temp_config_file, sample_config_data):
        """Test loading configuration from a JSON file."""
        # Mock the default config paths to be empty
        with patch.object(ConfigManager, 'DEFAULT_CONFIG_PATHS', []):
            config = ConfigManager.load_config(temp_config_file)
            
            assert config.api_key == sample_config_data["api_key"]
            assert config.endpoint == sample_config_data["endpoint"]
            assert config.timeout == sample_config_data["timeout"]
    
    def test_load_config_file_yaml(self, temp_yaml_config_file, sample_config_data):
        """Test loading configuration from a YAML file."""
        # Mock the default config paths to be empty
        with patch.object(ConfigManager, 'DEFAULT_CONFIG_PATHS', []):
            config = ConfigManager.load_config(temp_yaml_config_file)
            
            assert config.api_key == sample_config_data["api_key"]
            assert config.endpoint == sample_config_data["endpoint"]
            assert config.timeout == sample_config_data["timeout"]
    
    def test_load_config_from_env(self, monkeypatch):
        """Test loading configuration from environment variables."""
        # Mock the default config paths to be empty
        with patch.object(ConfigManager, 'DEFAULT_CONFIG_PATHS', []):
            # Set environment variables
            monkeypatch.setenv("MCP_API_KEY", "env-api-key")
            monkeypatch.setenv("MCP_ENDPOINT", "https://env-api.example.com")
            monkeypatch.setenv("MCP_TIMEOUT", "45")
            monkeypatch.setenv("MCP_MAX_RETRIES", "4")
            monkeypatch.setenv("MCP_VERIFY_SSL", "false")
            
            config = ConfigManager.load_config()
            
            assert config.api_key == "env-api-key"
            assert config.endpoint == "https://env-api.example.com"
            assert config.timeout == 45
            assert config.max_retries == 4
            assert config.verify_ssl is False
    
    def test_config_error_handling(self):
        """Test configuration error handling."""
        # Test missing required fields
        with pytest.raises(ValueError):
            MCPConfig(api_key="", endpoint="https://api.example.com")
            
        with pytest.raises(ValueError):
            MCPConfig(api_key="test-key", endpoint="")
            
        # Test invalid values
        with pytest.raises(ValueError):
            MCPConfig(
                api_key="test-key",
                endpoint="https://api.example.com",
                timeout=-1  # Timeout must be > 0
            )
            
        with pytest.raises(ValueError):
            MCPConfig(
                api_key="test-key",
                endpoint="https://api.example.com",
                max_retries=-1  # max_retries must be >= 0
            )

