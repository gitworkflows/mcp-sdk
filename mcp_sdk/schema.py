from typing import Dict, Any, List, Optional, Type, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class ArgumentType(str, Enum):
    """Supported argument types"""

    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    JSON = "json"
    LIST = "list"
    DICT = "dict"


class ArgumentSchema(BaseModel):
    """Schema for command arguments"""

    type: ArgumentType
    description: str
    required: bool = False
    default: Optional[Any] = None
    choices: Optional[List[Any]] = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    pattern: Optional[str] = None


class CommandSchema(BaseModel):
    """Schema for a command"""

    name: str
    description: str
    arguments: Dict[str, ArgumentSchema] = Field(default_factory=dict)
    options: Dict[str, ArgumentSchema] = Field(default_factory=dict)
    examples: List[str] = Field(default_factory=list)
    version: str = "1.0.0"


class SchemaManager:
    """Manages command schemas"""

    def __init__(self, schemas: Dict[str, Dict[str, Any]]):
        self.schemas = {
            name: CommandSchema(**schema) for name, schema in schemas.items()
        }

    def get_command_schema(self, command_name: str) -> Optional[CommandSchema]:
        """Get schema for a specific command"""
        return self.schemas.get(command_name)

    def validate_arguments(
        self, command_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate arguments against the command schema.

        Args:
            command_name: Name of the command
            arguments: Arguments to validate

        Returns:
            Dict[str, Any]: Validated arguments

        Raises:
            ValueError: If arguments are invalid
        """
        schema = self.get_command_schema(command_name)
        if not schema:
            raise ValueError(f"Unknown command: {command_name}")

        validated_args = {}

        # Validate required arguments
        for arg_name, arg_schema in schema.arguments.items():
            if arg_schema.required and arg_name not in arguments:
                raise ValueError(f"Missing required argument: {arg_name}")

            if arg_name in arguments:
                value = arguments[arg_name]
                validated_args[arg_name] = self._validate_value(
                    value, arg_schema, arg_name
                )

        # Validate options
        for opt_name, opt_schema in schema.options.items():
            if opt_name in arguments:
                value = arguments[opt_name]
                validated_args[opt_name] = self._validate_value(
                    value, opt_schema, opt_name
                )

        return validated_args

    def _validate_value(self, value: Any, schema: ArgumentSchema, name: str) -> Any:
        """Validate a single value against its schema"""
        try:
            # Type conversion
            if schema.type == ArgumentType.INTEGER:
                value = int(value)
            elif schema.type == ArgumentType.FLOAT:
                value = float(value)
            elif schema.type == ArgumentType.BOOLEAN:
                value = str(value).lower() == "true"
            elif schema.type == ArgumentType.JSON:
                if isinstance(value, str):
                    import json

                    value = json.loads(value)

            # Validate choices
            if schema.choices and value not in schema.choices:
                raise ValueError(
                    f"Invalid value for {name}. Must be one of: {schema.choices}"
                )

            # Validate min/max
            if schema.min is not None and value < schema.min:
                raise ValueError(f"Value for {name} must be >= {schema.min}")
            if schema.max is not None and value > schema.max:
                raise ValueError(f"Value for {name} must be <= {schema.max}")

            # Validate pattern
            if schema.pattern and isinstance(value, str):
                import re

                if not re.match(schema.pattern, value):
                    raise ValueError(
                        f"Value for {name} does not match pattern: {schema.pattern}"
                    )

            return value

        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid value for {name}: {str(e)}")

    def get_command_help(self, command_name: str) -> str:
        """Get help text for a command"""
        schema = self.get_command_schema(command_name)
        if not schema:
            return f"Unknown command: {command_name}"

        help_text = [
            f"Command: {command_name}",
            f"Description: {schema.description}",
            "\nArguments:",
        ]

        for arg_name, arg_schema in schema.arguments.items():
            help_text.append(
                f"  {arg_name}: {arg_schema.description}"
                f" (type: {arg_schema.type.value}, "
                f"required: {arg_schema.required})"
            )

        if schema.options:
            help_text.append("\nOptions:")
            for opt_name, opt_schema in schema.options.items():
                help_text.append(
                    f"  --{opt_name}: {opt_schema.description}"
                    f" (type: {opt_schema.type.value}, "
                    f"required: {opt_schema.required})"
                )

        if schema.examples:
            help_text.append("\nExamples:")
            help_text.extend(f"  {example}" for example in schema.examples)

        return "\n".join(help_text)
