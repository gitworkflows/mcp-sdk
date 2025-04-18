from mcp_sdk.server import MCPServer, ServerConfig

def main():
    # Create server configuration
    config = ServerConfig(
        host="0.0.0.0",
        port=8000,
        debug=True,
        workers=4,
        cors_origins=["http://localhost:3000"],
        cors_methods=["GET", "POST"],
        cors_headers=["Content-Type", "Authorization"]
    )

    # Initialize and run the server
    server = MCPServer(config)
    print("Starting MCP server...")
    server.run()

if __name__ == "__main__":
    main() 