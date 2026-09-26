import json
import httpx
import os
from pydantic import BaseModel
from typing import Optional
from app.agents.agent_state import AgentState
from app.agents.tool_registry import (
    get_available_tools,
    execute_builtin_tool,
    tool_requires_approval
)
from app.services.retrieval_service import retrieve_relevant_chunks
from app.services.llm_service import generate_answer
from app.core.logger import get_logger
from app.core.database import AsyncSessionLocal

logger = get_logger(__name__)



class RouteDecision(BaseModel):
    route: str
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None


TOOL_KEYWORDS = {
    "lookup_leave_balance": [
        "my leave balance", "leave balance", "how many days left",
        "remaining leave", "days remaining", "check my leave",
        "leave remaining"
    ],
    "submit_leave_request": [
        "submit leave", "apply for leave", "request leave",
        "take leave", "book leave", "leave request",
        "apply leave"
    ],
    "create_support_ticket": [
        "create ticket", "raise ticket", "open ticket",
        "submit ticket", "log issue", "report issue",
        "create a ticket"
    ],
    "get_ticket_status": [
        "ticket status", "check ticket", "status of ticket",
        "my ticket", "ticket update"
    ],
    "create_sales_lead": [
        "create lead", "new lead", "add lead",
        "sales lead", "potential customer"
    ],
    "schedule_callback": [
        "schedule callback", "call me back", "callback",
        "schedule a call"
    ]
}

UNANSWERABLE_KEYWORDS = [
    "weather", "sports", "news", "stock price",
    "recipe", "movie", "music", "game"
]


def keyword_route(question: str, tools_enabled: list[str]) -> tuple[str, str | None]:
    question_lower = question.lower()

    for keyword in UNANSWERABLE_KEYWORDS:
        if keyword in question_lower:
            return "unanswerable", None

    for tool_name in tools_enabled:
        if tool_name in TOOL_KEYWORDS:
            for pattern in TOOL_KEYWORDS[tool_name]:
                if pattern in question_lower:
                    return "tool_required", tool_name

    return "rag_only", None


async def extract_tool_input(
    question: str,
    tool_name: str,
    tool_info: dict
) -> dict:
    params = tool_info.get("parameters", {})
    param_descriptions = "\n".join([f"- {k}: {v}" for k, v in params.items()])

    prompt = f"""Extract parameters for tool "{tool_name}" from the question.

Parameters needed:
{param_descriptions}

Question: {question}

Respond with ONLY a JSON object with extracted parameters. No explanation."""

    try:
        from app.services.llm_service import call_groq
        content = await call_groq([
            {"role": "user", "content": prompt}
        ])
        # clean and parse JSON
        content = content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception as e:
        logger.error(f"Tool input extraction failed error={e}")
        return {}


async def router_node(state: AgentState) -> AgentState:
    logger.info(f"Router node question={state['question'][:50]}")

    tools_enabled = state.get("tools_enabled", [])
    available_tools = get_available_tools(tools_enabled)

    if not available_tools:
        logger.info("No tools enabled routing to rag_only")
        return {**state, "route": "rag_only"}

    route, tool_name = keyword_route(state["question"], tools_enabled)

    if route == "tool_required" and tool_name:
        logger.info(f"Keyword routing route={route} tool={tool_name}")
        tool_input = await extract_tool_input(
            state["question"],
            tool_name,
            available_tools[tool_name]
        )
        return {
            **state,
            "route": route,
            "tool_name": tool_name,
            "tool_input": tool_input
        }

    if route == "unanswerable":
        logger.info("Routing to unanswerable")
        return {**state, "route": "unanswerable"}

    logger.info("Routing to rag_only")
    return {**state, "route": "rag_only"}


async def retrieve_node(state: AgentState) -> AgentState:
    logger.info(f"Retrieve node question={state['question'][:50]}")

    try:
        chunks = await retrieve_relevant_chunks(
            question=state["question"],
            tenant_id=state["tenant_id"],
            agent_id=state["agent_id"],
            top_k=3,
            score_threshold=0.5
        )
        logger.info(f"Retrieved {len(chunks)} chunks")
        return {**state, "retrieved_chunks": chunks}

    except Exception as e:
        logger.error(f"Retrieve node failed error={e}")
        return {**state, "retrieved_chunks": [], "error": str(e)}


async def tool_node(state: AgentState) -> AgentState:
    """
    Executes a tool call.
    Supports both built-in tools and MCP tools.
    """
    tool_name = state.get("tool_name")
    tool_input = state.get("tool_input", {})

    logger.info(f"Tool node tool={tool_name} input={tool_input}")

    if not tool_name:
        return {**state, "route": "rag_only"}

    # check if this is an MCP tool
    mcp_servers = state.get("mcp_servers", [])
    is_mcp_tool = False
    mcp_server_url = None
    mcp_auth_key = None

    if mcp_servers:
        from app.services.mcp_service import get_all_available_tools
        all_tools = await get_all_available_tools(
            state.get("tools_enabled", []),
            mcp_servers
        )
        tool_info = all_tools.get(tool_name, {})
        if tool_info.get("source") == "mcp":
            is_mcp_tool = True
            mcp_server_url = tool_info.get("mcp_server_url")
            mcp_auth_key = tool_info.get("mcp_auth_key")

    # check approval requirement
    from app.agents.tool_registry import tool_requires_approval
    needs_approval = tool_requires_approval(tool_name)

    if needs_approval:
        logger.info(f"Tool requires approval tool={tool_name}")
        return {
            **state,
            "requires_approval": True,
            "approval_status": "pending",
            "tool_result": None
        }

    # execute tool
    try:
        if is_mcp_tool and mcp_server_url:
            from app.services.mcp_service import call_mcp_tool
            result = await call_mcp_tool(
                server_url=mcp_server_url,
                tool_name=tool_name,
                tool_input=tool_input,
                auth_key=mcp_auth_key
            )
            logger.info(f"MCP tool executed tool={tool_name}")
        else:
            from app.agents.tool_registry import execute_builtin_tool
            result = execute_builtin_tool(tool_name, tool_input)
            logger.info(f"Built-in tool executed tool={tool_name}")

        return {
            **state,
            "tool_result": result,
            "requires_approval": False
        }

    except Exception as e:
        logger.error(f"Tool execution failed tool={tool_name} error={e}")
        return {
            **state,
            "tool_result": {"error": str(e)},
            "requires_approval": False
        }


async def generate_node(state: AgentState) -> AgentState:
    logger.info("Generate node")

    chunks = state.get("retrieved_chunks", [])
    tool_result = state.get("tool_result")
    question = state["question"]
    system_prompt = state.get("system_prompt", "You are a helpful assistant.")

    if tool_result:
        tool_context = f"Tool Result: {json.dumps(tool_result, indent=2)}"
        chunks = chunks + [{
            "content": tool_context,
            "filename": "tool_result",
            "chunk_index": 0,
            "score": 1.0,
            "chunk_id": "tool"
        }]

    answer = await generate_answer(
        question=question,
        chunks=chunks,
        system_prompt=system_prompt
    )

    logger.info(f"Answer generated length={len(answer)}")
    return {**state, "answer": answer}


async def hitl_node(state: AgentState) -> AgentState:
    """
    Human in the loop node.
    Saves approval request to database.
    Manager can approve/reject via API.
    """
    logger.info("HITL node - saving approval request")

    tool_name = state.get("tool_name", "unknown")
    tool_input = state.get("tool_input", {})

    try:
        async with AsyncSessionLocal() as db:
            from app.services.hitl_service import create_approval_request
            approval = await create_approval_request(
                tenant_id=state["tenant_id"],
                agent_id=state["agent_id"],
                user_id=state["user_id"],
                tool_name=tool_name,
                tool_input=tool_input,
                agent_state=dict(state),
                conversation_id=state.get("conversation_id", "") or None,
                db=db
            )

        answer = (
            f"The action '{tool_name}' requires manager approval. "
            f"Your request has been submitted (ID: {approval.id}). "
            f"You will be notified once a decision is made. "
            f"Approval expires in 24 hours."
        )
        logger.info(f"Approval request created id={approval.id}")

    except Exception as e:
        logger.error(f"Failed to create approval request error={e}")
        answer = (
            f"The action '{tool_name}' requires manager approval "
            f"but we could not save the request. Please try again."
        )

    return {**state, "answer": answer}