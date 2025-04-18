import argparse
import sys
from typing import Dict, Any, Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import print as rprint

from .client import MCPClient
from .config import ConfigManager, MCPConfig
from .schema import SchemaManager
from .exceptions import MCPError

class MCPCLI:
    """CLI tool for interacting with MCP servers"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the CLI tool.

        Args:
            config_path: Path to the configuration file
        """
        self.console = Console()
        self.config = ConfigManager.load_config(config_path)
        self.client = None
        self.schema_manager = None

    def _connect(self):
        """Connect to the MCP server and load schemas"""
        if not self.client:
            try:
                self.client = MCPClient(
                    api_key=self.config.api_key,
                    endpoint=self.config.endpoint,
                    timeout=self.config.timeout,
                    max_retries=self.config.max_retries,
                    retry_backoff_factor=self.config.retry_backoff_factor,
                    verify_ssl=self.config.verify_ssl
                )
                self._load_schemas()
            except Exception as e:
                self.console.print(f"[red]Error connecting to server: {str(e)}[/red]")
                sys.exit(1)

    def _load_schemas(self):
        """Load command schemas from the MCP server"""
        try:
            response = self.client.send({
                "type": "get_schemas",
                "options": {"include_raw": True}
            })
            self.schema_manager = SchemaManager(response.data)
        except Exception as e:
            self.console.print(f"[red]Error loading schemas: {str(e)}[/red]")
            sys.exit(1)

    def _build_parser(self) -> argparse.ArgumentParser:
        """Build the argument parser"""
        parser = argparse.ArgumentParser(
            description="MCP CLI Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Add commands from schemas
        for command_name in self.schema_manager.schemas.keys():
            schema = self.schema_manager.get_command_schema(command_name)
            subparser = subparsers.add_parser(
                command_name,
                help=schema.description,
                formatter_class=argparse.RawDescriptionHelpFormatter
            )

            # Add arguments
            for arg_name, arg_schema in schema.arguments.items():
                subparser.add_argument(
                    arg_name,
                    help=arg_schema.description,
                    type=self._get_type(arg_schema.type),
                    required=arg_schema.required,
                    choices=arg_schema.choices
                )

            # Add options
            for opt_name, opt_schema in schema.options.items():
                subparser.add_argument(
                    f"--{opt_name}",
                    help=opt_schema.description,
                    type=self._get_type(opt_schema.type),
                    required=opt_schema.required,
                    choices=opt_schema.choices
                )

            subparser.set_defaults(func=self._create_handler(command_name))

        return parser

    def _get_type(self, arg_type: str) -> type:
        """Convert argument type string to Python type"""
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "json": self._parse_json,
            "list": self._parse_list,
            "dict": self._parse_dict
        }
        return type_map.get(arg_type, str)

    def _parse_json(self, value: str) -> dict:
        """Parse JSON string"""
        import json
        return json.loads(value)

    def _parse_list(self, value: str) -> list:
        """Parse comma-separated list"""
        return [item.strip() for item in value.split(",")]

    def _parse_dict(self, value: str) -> dict:
        """Parse key=value pairs"""
        return dict(item.split("=") for item in value.split(","))

    def _create_handler(self, command_name: str):
        """Create a command handler"""
        def handler(args):
            try:
                # Convert args to dict
                args_dict = vars(args)
                del args_dict['func']  # Remove the handler function

                # Validate arguments
                validated_args = self.schema_manager.validate_arguments(
                    command_name,
                    args_dict
                )

                # Send request to server
                response = self.client.send({
                    "type": command_name,
                    "arguments": validated_args
                })

                # Display response
                self._display_response(response)

            except Exception as e:
                self.console.print(f"[red]Error executing command: {str(e)}[/red]")
                sys.exit(1)

        return handler

    def _display_response(self, response: Any):
        """Display response in a formatted way"""
        if isinstance(response, dict):
            if "data" in response:
                if isinstance(response["data"], list):
                    self._display_table(response["data"])
                else:
                    self._display_object(response["data"])
            else:
                self._display_object(response)
        elif isinstance(response, list):
            self._display_table(response)
        else:
            rprint(response)

    def _display_table(self, data: list):
        """Display data in a table format"""
        if not data:
            return

        table = Table(show_header=True, header_style="bold magenta")

        # Add columns based on first item's keys
        for key in data[0].keys():
            table.add_column(key)

        # Add rows
        for item in data:
            table.add_row(*[str(item.get(key, "")) for key in data[0].keys()])

        self.console.print(table)

    def _display_object(self, obj: dict):
        """Display object in a formatted way"""
        if not obj:
            return

        # Create a table with two columns: key and value
        table = Table(show_header=False, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")

        # Add rows for each key-value pair
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                value = str(value)
            table.add_row(key, str(value))

        self.console.print(table)

    def run(self):
        """Run the CLI tool"""
        try:
            self._connect()
            parser = self._build_parser()
            args = parser.parse_args()

            if not args.command:
                # Display available commands
                self._display_available_commands()
                return

            args.func(args)

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/red]")
            sys.exit(1)
        finally:
            if self.client:
                self.client.close()

    def _display_available_commands(self):
        """Display available commands and their descriptions"""
        self.console.print(Panel.fit(
            "[bold]MCP CLI Tool[/bold]\n"
            "Available commands:",
            title="MCP CLI"
        ))

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Command")
        table.add_column("Description")

        for command_name, schema in self.schema_manager.schemas.items():
            table.add_row(command_name, schema.description)

        self.console.print(table)
        self.console.print("\nUse 'mcp <command> --help' for detailed command information")

def main():
    """Entry point for the CLI tool"""
    parser = argparse.ArgumentParser(description="MCP CLI Tool")
    parser.add_argument(
        "--config",
        help="Path to configuration file",
        default=None
    )
    args = parser.parse_args()

    cli = MCPCLI(args.config)
    cli.run()

if __name__ == "__main__":
    main() 