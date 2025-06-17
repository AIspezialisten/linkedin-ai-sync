"""
LinkedIn MCP Server for Member Snapshot API integration.

This server provides tools to interact with LinkedIn's Member Data Portability API,
specifically the Member Snapshot API for retrieving member profile data.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    EmbeddedResource,
)
from pydantic import BaseModel


class LinkedInConfig(BaseModel):
    """Configuration for LinkedIn API access."""
    access_token: str
    api_version: str = "202312"
    base_url: str = "https://api.linkedin.com"


class LinkedInMemberSnapshot(BaseModel):
    """LinkedIn Member Snapshot data model."""
    id: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    industryName: Optional[str] = None
    summary: Optional[str] = None
    positions: List[Dict[str, Any]] = []
    educations: List[Dict[str, Any]] = []
    skills: List[Dict[str, Any]] = []


class LinkedInMCPServer:
    """LinkedIn MCP Server implementation."""

    def __init__(self):
        self.server = Server("linkedin-mcp")
        self.client: Optional[httpx.AsyncClient] = None
        self.config: Optional[LinkedInConfig] = None
        
        # Register tools
        self.server.list_tools = self._list_tools
        self.server.call_tool = self._call_tool

    async def _initialize_client(self) -> None:
        """Initialize HTTP client and configuration."""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
            
        if self.config is None:
            access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
            if not access_token:
                raise ValueError("LINKEDIN_ACCESS_TOKEN environment variable is required")
            
            self.config = LinkedInConfig(access_token=access_token)

    async def _list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """List available LinkedIn tools."""
        return ListToolsResult(
            tools=[
                Tool(
                    name="get_member_snapshot_data",
                    description="Retrieve member snapshot data from LinkedIn Member Data Portability API",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "domain": {
                                "type": "string",
                                "description": "Data domain to query (e.g., 'CONNECTIONS', 'PROFILE')",
                                "default": "CONNECTIONS"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_connections_data",
                    description="Get LinkedIn connections data specifically",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        )

    async def _call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Execute LinkedIn tool calls."""
        await self._initialize_client()
        
        try:
            if request.params.name == "get_member_snapshot_data":
                return await self._get_member_snapshot_data(request.params.arguments or {})
            elif request.params.name == "get_connections_data":
                return await self._get_connections_data(request.params.arguments or {})
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unknown tool: {request.params.name}")]
                )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True
            )

    async def _get_member_snapshot_data(self, args: Dict[str, Any]) -> CallToolResult:
        """Retrieve LinkedIn member snapshot data using the Member Snapshot Data API."""
        domain = args.get("domain", "CONNECTIONS")
        
        headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "LinkedIn-Version": self.config.api_version,
            "Content-Type": "application/json"
        }
        
        # LinkedIn Member Snapshot Data API endpoint (the one that works)
        url = f"{self.config.base_url}/rest/memberSnapshotData"
        params = {
            "q": "criteria",
            "domain": domain
        }
        
        response = await self.client.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        return CallToolResult(
            content=[TextContent(
                type="text", 
                text=json.dumps(data, indent=2)
            )]
        )

    async def _get_connections_data(self, args: Dict[str, Any]) -> CallToolResult:
        """Get LinkedIn connections data specifically."""
        headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "LinkedIn-Version": self.config.api_version,
            "Content-Type": "application/json"
        }
        
        # LinkedIn Member Snapshot Data API for connections
        url = f"{self.config.base_url}/rest/memberSnapshotData"
        params = {
            "q": "criteria",
            "domain": "CONNECTIONS"
        }
        
        response = await self.client.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract connections from the response
        connections = []
        if "elements" in data:
            for element in data["elements"]:
                if "memberConnections" in element:
                    connections.extend(element["memberConnections"].get("elements", []))
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "connections": connections,
                    "total_count": len(connections),
                    "raw_response": data
                }, indent=2)
            )]
        )

    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            await self.client.aclose()


async def main():
    """Main entry point for LinkedIn MCP server."""
    linkedin_server = LinkedInMCPServer()
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            await linkedin_server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="linkedin-mcp",
                    server_version="0.1.0",
                    capabilities=linkedin_server.server.get_capabilities(
                        notification=False,
                        experimental={}
                    )
                )
            )
    finally:
        await linkedin_server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())