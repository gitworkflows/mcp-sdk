# scratch_mcp.py

from mcp_sdk.client import MCPClient

# Initialize the MCP client
client = MCPClient(api_key="your-api-key", endpoint="http://localhost:8000")

# Example input
input_data = {
    "model": "gpt-4",
    "context": "This is a test message",
    "settings": {
        "temperature": 0.7,
        "max_tokens": 150
    }
}

# Send data to MCP and get the response
response = client.send(input_data)

# Print the response
print("Response from MCP:")
print(response)

