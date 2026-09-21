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

logger = get_logger(__name__)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "ollama")
OLLAMA_PORT = os.environ.get("OLLAMA_PORT", "11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3.2:3b")
OLLAMA_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"


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

Parameters:
{param_descriptions}

Question: {question}

Respond with ONLY a JSON object with extracted parameters."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "format": "json",
                    "stream": False
                }
            )
            response.raise_for_status()
            content = response.json()["message"]["content"]
            return json.loads(content)
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
    tool_name = state.get("tool_name")
    tool_input = state.get("tool_input", {})

    logger.info(f"Tool node tool={tool_name} input={tool_input}")

    if not tool_name:
        return {**state, "route": "rag_only"}

    needs_approval = tool_requires_approval(tool_name)

    if needs_approval:
        logger.info(f"Tool requires approval tool={tool_name}")
        return {
            **state,
            "requires_approval": True,
            "approval_status": "pending",
            "tool_result": None
        }

    try:
        result = execute_builtin_tool(tool_name, tool_input)
        logger.info(f"Tool executed successfully tool={tool_name}")
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
    logger.info("HITL node approval required")
    tool_name = state.get("tool_name", "action")
    answer = (
        f"The action '{tool_name}' requires manager approval "
        f"before it can be executed. "
        f"A notification has been sent to your manager. "
        f"You will be notified once a decision is made."
    )
    return {**state, "answer": answer}