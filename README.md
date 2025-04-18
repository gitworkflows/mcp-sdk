# MCP SDK

A Python SDK for interacting with the Media Control Protocol (MCP) API.

## Installation

```bash
pip install mcp-sdk
```

## Quick Start

```python
from mcp_sdk.client import MCPClient

# Initialize the client
client = MCPClient(
    api_key="your-api-key",
    endpoint="http://localhost:8000"
)

# Example usage
input_data = {
    "model": "gpt-4",
    "context": "This is a test message",
    "settings": {
        "temperature": 0.7,
        "max_tokens": 150
    }
}

# Send data to MCP
response = client.send(input_data)
print(response)
```

## Features

- Easy-to-use Python interface for MCP API
- Type-safe request and response handling
- Automatic retry mechanism for failed requests
- Comprehensive error handling
- Async support

## Documentation

For detailed documentation, please visit [documentation link].

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 