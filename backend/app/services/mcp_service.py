import httpx
import json
from app.core.logger import get_logger

logger = get_logger(__name__)


async def discover_mcp_tools(server_url: str, auth_key: str = None) -> list[dict]:
    """
    Connect to an MCP server and discover what tools it offers.
    Returns list of tool definitions.
    """
    headers = {"Content-Type": "application/json"}
    if auth_key:
        headers["Authorization"] = f"Bearer {auth_key}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # MCP tool discovery endpoint
            response = await client.get(
                f"{server_url}/tools",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            tools = data.get("tools", [])
            logger.info(
                f"Discovered {len(tools)} tools "
                f"from MCP server {server_url}"
            )
            return tools
    except Exception as e:
        logger.error(f"Failed to discover MCP tools server={server_url} error={e}")
        return []


async def call_mcp_tool(
    server_url: str,
    tool_name: str,
    tool_input: dict,
    auth_key: str = None
) -> dict:
    """
    Call a tool on an MCP server.
    Returns the tool result.
    """
    headers = {"Content-Type": "application/json"}
    if auth_key:
        headers["Authorization"] = f"Bearer {auth_key}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{server_url}/tools/{tool_name}",
                headers=headers,
                json=tool_input
            )
            response.raise_for_status()
            result = response.json()
            logger.info(
                f"MCP tool called successfully "
                f"tool={tool_name} "
                f"server={server_url}"
            )
            return result
    except Exception as e:
        logger.error(
            f"MCP tool call failed "
            f"tool={tool_name} "
            f"server={server_url} "
            f"error={e}"
        )
        return {"error": str(e)}


async def get_all_available_tools(
    builtin_tools: list[str],
    mcp_servers: list[dict]
) -> dict:
    """
    Combine built-in tools and MCP tools into one registry.
    
    Returns dict of all available tools with their descriptions.
    """
    from app.agents.tool_registry import get_available_tools

    # start with built-in tools
    all_tools = get_available_tools(builtin_tools)

    # add MCP tools
    for server_config in mcp_servers:
        server_url = server_config.get("url")
        server_name = server_config.get("name", server_url)
        auth_key = server_config.get("auth_key")

        if not server_url:
            continue

        mcp_tools = await discover_mcp_tools(server_url, auth_key)

        for tool in mcp_tools:
            tool_name = tool.get("name")
            if tool_name:
                all_tools[tool_name] = {
                    "description": tool.get("description", ""),
                    "requires_approval": tool.get("requires_approval", False),
                    "parameters": tool.get("inputSchema", {}).get("properties", {}),
                    "source": "mcp",
                    "mcp_server_url": server_url,
                    "mcp_auth_key": auth_key
                }
                logger.debug(f"Added MCP tool tool={tool_name} server={server_name}")

    logger.info(
        f"Total available tools: {len(all_tools)} "
        f"(builtin={len(builtin_tools)}, "
        f"mcp_servers={len(mcp_servers)})"
    )
    return all_tools