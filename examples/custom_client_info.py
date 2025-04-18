from mcp_sdk import MCPClient

def main():
    # Basic client initialization
    client = MCPClient(
        api_key="your-api-key",
        endpoint="http://localhost:8000"
    )

    # Client with custom info
    custom_client = MCPClient(
        api_key="your-api-key",
        endpoint="http://localhost:8000",
        client_info={
            "name": "my-awesome-app",
            "version": "1.0.0",
            "environment": "development",
            "client_id": "my-client-123",
            "metadata": {
                "app_type": "web",
                "framework": "django",
                "deployment": "kubernetes"
            }
        },
        # Additional configuration
        timeout=60,
        max_retries=5,
        retry_backoff_factor=1.0,
        verify_ssl=False,
        headers={
            "X-Custom-Header": "custom-value"
        },
        proxy={
            "http": "http://proxy.example.com:8080",
            "https": "http://proxy.example.com:8080"
        }
    )

    try:
        # Make a request with the custom client
        response = custom_client.send({
            "operation": "test",
            "data": {
                "message": "Hello from custom client!"
            }
        })
        print("Response:", response)

        # Access client information
        print("\nClient Info:")
        print(f"Name: {custom_client.client_info.name}")
        print(f"Version: {custom_client.client_info.version}")
        print(f"Environment: {custom_client.client_info.environment}")
        print(f"Platform: {custom_client.client_info.platform}")
        print(f"Metadata: {custom_client.client_info.metadata}")

    except Exception as e:
        print(f"Error: {str(e)}")

    finally:
        # Always close the clients
        client.close()
        custom_client.close()

if __name__ == "__main__":
    main() 