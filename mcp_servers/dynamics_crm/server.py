"""
Microsoft Dynamics CRM MCP Server for CRM API integration.

This server provides tools to interact with Microsoft Dynamics CRM Web API
for managing contacts, accounts, and other CRM entities.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

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
)
from pydantic import BaseModel


class DynamicsCRMConfig(BaseModel):
    """Configuration for Dynamics CRM API access."""
    tenant_id: str
    client_id: str
    client_secret: str
    crm_url: str  # e.g., https://org.crm.dynamics.com
    api_version: str = "v9.2"


class CRMContact(BaseModel):
    """Dynamics CRM Contact entity model."""
    contactid: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    fullname: Optional[str] = None
    emailaddress1: Optional[str] = None
    jobtitle: Optional[str] = None
    telephone1: Optional[str] = None
    mobilephone: Optional[str] = None
    address1_line1: Optional[str] = None
    address1_city: Optional[str] = None
    address1_stateorprovince: Optional[str] = None
    address1_postalcode: Optional[str] = None
    address1_country: Optional[str] = None
    description: Optional[str] = None
    linkedin_profile: Optional[str] = None  # Custom field for LinkedIn profile URL


class DynamicsCRMMCPServer:
    """Microsoft Dynamics CRM MCP Server implementation."""

    def __init__(self):
        self.server = Server("dynamics-crm-mcp")
        self.client: Optional[httpx.AsyncClient] = None
        self.config: Optional[DynamicsCRMConfig] = None
        self.access_token: Optional[str] = None
        
        # Register tools
        self.server.list_tools = self._list_tools
        self.server.call_tool = self._call_tool

    async def _initialize_client(self) -> None:
        """Initialize HTTP client and configuration."""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
            
        if self.config is None:
            self.config = DynamicsCRMConfig(
                tenant_id=os.getenv("DYNAMICS_TENANT_ID", ""),
                client_id=os.getenv("DYNAMICS_CLIENT_ID", ""),
                client_secret=os.getenv("DYNAMICS_CLIENT_SECRET", ""),
                crm_url=os.getenv("DYNAMICS_CRM_URL", "")
            )
            
            if not all([self.config.tenant_id, self.config.client_id, 
                       self.config.client_secret, self.config.crm_url]):
                raise ValueError("Missing required Dynamics CRM environment variables")

    async def _get_access_token(self) -> str:
        """Get OAuth access token for Dynamics CRM."""
        if self.access_token:
            return self.access_token
            
        token_url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": f"{self.config.crm_url}/.default"
        }
        
        response = await self.client.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        return self.access_token

    async def _list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """List available Dynamics CRM tools."""
        return ListToolsResult(
            tools=[
                Tool(
                    name="create_contact",
                    description="Create a new contact in Dynamics CRM",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "firstname": {"type": "string", "description": "First name"},
                            "lastname": {"type": "string", "description": "Last name"},
                            "emailaddress1": {"type": "string", "description": "Primary email address"},
                            "jobtitle": {"type": "string", "description": "Job title"},
                            "telephone1": {"type": "string", "description": "Primary phone number"},
                            "mobilephone": {"type": "string", "description": "Mobile phone number"},
                            "address1_line1": {"type": "string", "description": "Address line 1"},
                            "address1_city": {"type": "string", "description": "City"},
                            "address1_stateorprovince": {"type": "string", "description": "State or province"},
                            "address1_postalcode": {"type": "string", "description": "Postal code"},
                            "address1_country": {"type": "string", "description": "Country"},
                            "description": {"type": "string", "description": "Description or notes"},
                            "linkedin_profile": {"type": "string", "description": "LinkedIn profile URL"}
                        },
                        "required": ["lastname"]
                    }
                ),
                Tool(
                    name="get_contact",
                    description="Retrieve a contact from Dynamics CRM by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "contact_id": {
                                "type": "string",
                                "description": "Contact ID (GUID)"
                            }
                        },
                        "required": ["contact_id"]
                    }
                ),
                Tool(
                    name="search_contacts",
                    description="Search contacts in Dynamics CRM",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter": {
                                "type": "string",
                                "description": "OData filter expression (e.g., \"contains(fullname,'John')\")"
                            },
                            "select": {
                                "type": "string",
                                "description": "Comma-separated list of fields to select"
                            },
                            "top": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "minimum": 1,
                                "maximum": 1000
                            }
                        }
                    }
                ),
                Tool(
                    name="update_contact",
                    description="Update an existing contact in Dynamics CRM",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "contact_id": {
                                "type": "string",
                                "description": "Contact ID (GUID)"
                            },
                            "data": {
                                "type": "object",
                                "description": "Contact data to update",
                                "properties": {
                                    "firstname": {"type": "string"},
                                    "lastname": {"type": "string"},
                                    "emailaddress1": {"type": "string"},
                                    "jobtitle": {"type": "string"},
                                    "telephone1": {"type": "string"},
                                    "mobilephone": {"type": "string"},
                                    "description": {"type": "string"},
                                    "linkedin_profile": {"type": "string"}
                                }
                            }
                        },
                        "required": ["contact_id", "data"]
                    }
                )
            ]
        )

    async def _call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Execute Dynamics CRM tool calls."""
        await self._initialize_client()
        
        try:
            if request.params.name == "create_contact":
                return await self._create_contact(request.params.arguments or {})
            elif request.params.name == "get_contact":
                return await self._get_contact(request.params.arguments or {})
            elif request.params.name == "search_contacts":
                return await self._search_contacts(request.params.arguments or {})
            elif request.params.name == "update_contact":
                return await self._update_contact(request.params.arguments or {})
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unknown tool: {request.params.name}")]
                )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True
            )

    async def _create_contact(self, args: Dict[str, Any]) -> CallToolResult:
        """Create a new contact in Dynamics CRM."""
        access_token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0"
        }
        
        # Build contact data
        contact_data = {k: v for k, v in args.items() if v is not None}
        
        url = urljoin(self.config.crm_url, f"/api/data/{self.config.api_version}/contacts")
        
        response = await self.client.post(url, headers=headers, json=contact_data)
        response.raise_for_status()
        
        # Get the created contact ID from the response headers
        contact_id = response.headers.get("OData-EntityId", "").split("(")[-1].rstrip(")")
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "contact_id": contact_id,
                    "message": "Contact created successfully"
                }, indent=2)
            )]
        )

    async def _get_contact(self, args: Dict[str, Any]) -> CallToolResult:
        """Retrieve a contact from Dynamics CRM."""
        contact_id = args["contact_id"]
        access_token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0"
        }
        
        url = urljoin(self.config.crm_url, f"/api/data/{self.config.api_version}/contacts({contact_id})")
        
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        
        contact_data = response.json()
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(contact_data, indent=2)
            )]
        )

    async def _search_contacts(self, args: Dict[str, Any]) -> CallToolResult:
        """Search contacts in Dynamics CRM."""
        access_token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0"
        }
        
        url = urljoin(self.config.crm_url, f"/api/data/{self.config.api_version}/contacts")
        
        params = {}
        if args.get("filter"):
            params["$filter"] = args["filter"]
        if args.get("select"):
            params["$select"] = args["select"]
        if args.get("top"):
            params["$top"] = args["top"]
        else:
            params["$top"] = 50  # Default limit
        
        response = await self.client.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
        )

    async def _update_contact(self, args: Dict[str, Any]) -> CallToolResult:
        """Update an existing contact in Dynamics CRM."""
        contact_id = args["contact_id"]
        update_data = args["data"]
        access_token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0"
        }
        
        url = urljoin(self.config.crm_url, f"/api/data/{self.config.api_version}/contacts({contact_id})")
        
        response = await self.client.patch(url, headers=headers, json=update_data)
        response.raise_for_status()
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "message": "Contact updated successfully"
                }, indent=2)
            )]
        )

    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            await self.client.aclose()


async def main():
    """Main entry point for Dynamics CRM MCP server."""
    crm_server = DynamicsCRMMCPServer()
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            await crm_server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="dynamics-crm-mcp",
                    server_version="0.1.0",
                    capabilities=crm_server.server.get_capabilities(
                        notification=False,
                        experimental={}
                    )
                )
            )
    finally:
        await crm_server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())