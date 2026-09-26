"""
Mock HR MCP Server using MCP 2.x
"""
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp import types
from starlette.applications import Starlette
from starlette.routing import Route
import uvicorn

app = Server("acme-hr-system")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_leave_balance",
            description="Get the current leave balance for an employee",
            inputSchema={
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "The unique employee identifier"
                    }
                },
                "required": ["employee_id"]
            }
        ),
        types.Tool(
            name="get_employee_info",
            description="Get basic information about an employee",
            inputSchema={
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "The unique employee identifier"
                    }
                },
                "required": ["employee_id"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "get_leave_balance":
        employee_id = arguments.get("employee_id")
        mock_data = {
            "EMP001": {"annual": 15, "sick": 8, "carried_forward": 2},
            "EMP002": {"annual": 10, "sick": 10, "carried_forward": 0},
        }
        if employee_id not in mock_data:
            result = {"error": f"Employee {employee_id} not found"}
        else:
            balance = mock_data[employee_id]
            result = {
                "employee_id": employee_id,
                "annual_leave_remaining": balance["annual"],
                "sick_leave_remaining": balance["sick"],
                "carried_forward": balance["carried_forward"]
            }
        return [types.TextContent(type="text", text=str(result))]

    elif name == "get_employee_info":
        employee_id = arguments.get("employee_id")
        mock_employees = {
            "EMP001": {"name": "John Smith", "department": "Engineering"},
            "EMP002": {"name": "Mary Johnson", "department": "Marketing"},
        }
        if employee_id not in mock_employees:
            result = {"error": f"Employee {employee_id} not found"}
        else:
            result = {"employee_id": employee_id, **mock_employees[employee_id]}
        return [types.TextContent(type="text", text=str(result))]

    return [types.TextContent(type="text", text="Unknown tool")]


# create SSE transport
sse = SseServerTransport("/messages/")

async def handle_sse(request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await app.run(
            streams[0], streams[1], app.create_initialization_options()
        )

async def handle_messages(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

starlette_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages/", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    uvicorn.run(starlette_app, host="0.0.0.0", port=8001)