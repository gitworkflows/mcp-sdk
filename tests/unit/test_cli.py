import pytest
from unittest.mock import patch, Mock
import sys
import io

from mcp_sdk.cli import MCPCLI, main
from mcp_sdk.config import ConfigManager

class TestCLI:
    """Tests for the CLI interface."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock()
        config.api_key = "test-api-key"
        config.endpoint = "https://api.example.com"
        return config
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock client."""
        client = Mock()
        client.send.return_value = {"result": "success"}
        return client
    
    @pytest.fixture
    def mock_schema_manager(self):
        """Create a mock schema manager."""
        schema_manager = Mock()
        
        # Mock command schema
        command_schema = Mock()
        command_schema.description = "Test command"
        command_schema.arguments = {
            "arg1": Mock(description="Test arg", type="str", required=True, choices=None)
        }
        command_schema.options = {
            "opt1": Mock(description="Test option", type="str", required=False, choices=None)
        }
        
        schema_manager.schemas = {"test-command": command_schema}
        schema_manager.get_command_schema.return_value = command_schema
        schema_manager.validate_arguments.return_value = {"arg1": "value1"}
        
        return schema_manager
    
    def test_cli_initialization(self, mock_config):
        """Test CLI initialization."""
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            cli = MCPCLI()
            assert cli.config == mock_config
            assert cli.client is None
            assert cli.schema_manager is None
    
    def test_cli_connect(self, mock_config, mock_client):
        """Test CLI connection establishment."""
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            with patch('mcp_sdk.cli.MCPClient', return_value=mock_client):
                cli = MCPCLI()
                cli._connect()
                
                assert cli.client == mock_client
    
    def test_cli_load_schemas(self, mock_config, mock_client, mock_schema_manager):
        """Test loading command schemas."""
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            with patch('mcp_sdk.cli.MCPClient', return_value=mock_client):
                with patch('mcp_sdk.cli.SchemaManager', return_value=mock_schema_manager):
                    cli = MCPCLI()
                    cli.client = mock_client
                    cli._load_schemas()
                    
                    assert cli.schema_manager == mock_schema_manager
                    mock_client.send.assert_called_once()
    
    def test_cli_build_parser(self, mock_config, mock_schema_manager):
        """Test argument parser building."""
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            cli = MCPCLI()
            cli.schema_manager = mock_schema_manager
            
            parser = cli._build_parser()
            
            assert parser.description == "MCP CLI Tool"
            # Ensure subparsers were created
            assert hasattr(parser, '_subparsers')
    
    def test_cli_display_available_commands(self, mock_config, mock_schema_manager):
        """Test displaying available commands."""
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            cli = MCPCLI()
            cli.schema_manager = mock_schema_manager
            cli.console = Mock()
            
            cli._display_available_commands()
            
            # Verify console was used to display information
            assert cli.console.print.call_count >= 2
    
    def test_cli_command_handler(self, mock_config, mock_client, mock_schema_manager):
        """Test command handler creation and execution."""
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            cli = MCPCLI()
            cli.client = mock_client
            cli.schema_manager = mock_schema_manager
            cli.console = Mock()
            
            # Create a handler for a test command
            handler = cli._create_handler("test-command")
            
            # Create mock args
            args = Mock()
            args.__dict__ = {"func": handler, "arg1": "value1", "opt1": "option1"}
            
            # Execute the handler
            handler(args)
            
            # Verify validations and client calls
            mock_schema_manager.validate_arguments.assert_called_once()
            mock_client.send.assert_called_once_with({
                "type": "test-command",
                "arguments": {"arg1": "value1"}
            })
            cli.console.print.assert_called()  # Verify output was displayed

    def test_cli_error_handling(self, mock_config, mock_client):
        """Test CLI error handling."""
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            cli = MCPCLI()
            cli.console = Mock()
            
            # Test connection error
            with patch('mcp_sdk.cli.MCPClient', side_effect=ConnectionError("Connection failed")):
                with pytest.raises(SystemExit):
                    cli._connect()
                cli.console.print.assert_called_with("[red]Error connecting to server: Connection failed[/red]")

    def test_cli_type_conversion(self, mock_config):
        """Test CLI argument type conversion."""
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            cli = MCPCLI()
            
            # Test JSON conversion
            json_str = '{"key": "value"}'
            result = cli._parse_json(json_str)
            assert result == {"key": "value"}
            
            # Test list conversion
            list_str = "item1,item2,item3"
            result = cli._parse_list(list_str)
            assert result == ["item1", "item2", "item3"]
            
            # Test dict conversion
            dict_str = "key1=value1,key2=value2"
            result = cli._parse_dict(dict_str)
            assert result == {"key1": "value1", "key2": "value2"}

    def test_cli_display_response_dict(self, mock_config):
        """Test displaying dictionary responses."""
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            cli = MCPCLI()
            cli.console = Mock()
            
            # Test with dict containing data
            response = {"data": {"key": "value"}}
            cli._display_response(response)
            cli.console.print.assert_called()
            
            # Test with dict containing list
            response = {"data": [{"item": 1}, {"item": 2}]}
            cli._display_response(response)
            cli.console.print.assert_called()

    def test_cli_display_response_list(self, mock_config):
        """Test displaying list responses."""
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            cli = MCPCLI()
            cli.console = Mock()
            
            # Test with list
            response = [{"item": 1}, {"item": 2}]
            cli._display_response(response)
            cli.console.print.assert_called()

    def test_cli_run(self, mock_config, mock_client, mock_schema_manager):
        """Test CLI run method."""
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            with patch('mcp_sdk.cli.MCPClient', return_value=mock_client):
                with patch('mcp_sdk.cli.SchemaManager', return_value=mock_schema_manager):
                    with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
                        cli = MCPCLI()
                        
                        # Test with command
                        args = Mock()
                        args.command = "test-command"
                        args.func = Mock()
                        mock_parse_args.return_value = args
                        
                        cli.run()
                        
                        args.func.assert_called_once_with(args)
                        mock_client.close.assert_called_once()

    def test_cli_run_no_command(self, mock_config, mock_schema_manager):
        """Test CLI run method with no command."""
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
                cli = MCPCLI()
                cli.schema_manager = mock_schema_manager
                cli.console = Mock()
                
                # Test without command
                args = Mock()
                args.command = None
                mock_parse_args.return_value = args
                
                cli.run()
                
                # Should display available commands
                cli.console.print.assert_called()

    def test_main_function(self):
        """Test the main function."""
        with patch('mcp_sdk.cli.MCPCLI') as mock_cli_class:
            mock_cli = Mock()
            mock_cli_class.return_value = mock_cli
            
            with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
                args = Mock()
                args.config = "test-config.json"
                mock_parse_args.return_value = args
                
                main()
                
                mock_cli_class.assert_called_once_with("test-config.json")
                mock_cli.run.assert_called_once()
