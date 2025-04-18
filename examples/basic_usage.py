from mcp_sdk.client import MCPClient

def main():
    # Initialize the client
    client = MCPClient(
        api_key="your-api-key",
        endpoint="http://localhost:8000"
    )

    try:
        # Prepare the request data
        input_data = {
            "model": "gpt-4",
            "context": "This is a test message",
            "settings": {
                "temperature": 0.7,
                "max_tokens": 150
            }
        }

        # Send the request
        response = client.send(input_data)

        # Print the response
        print("Response from MCP:")
        print(f"ID: {response.id}")
        print(f"Model: {response.model}")
        print(f"Content: {response.content}")
        print(f"Created at: {response.created_at}")
        print(f"Usage: {response.usage}")

    except Exception as e:
        print(f"Error: {str(e)}")

    finally:
        # Always close the client
        client.close()

if __name__ == "__main__":
    main() 