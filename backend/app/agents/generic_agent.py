from langgraph.graph import StateGraph, END
from app.agents.agent_state import AgentState
from app.agents.nodes import (
    router_node,
    retrieve_node,
    tool_node,
    generate_node,
    hitl_node
)
from app.core.logger import get_logger

logger = get_logger(__name__)


def route_after_router(state: AgentState) -> str:
    route = state.get("route", "rag_only")
    if route == "tool_required":
        return "tool"
    elif route == "unanswerable":
        return "generate"
    else:
        return "retrieve"


def route_after_tool(state: AgentState) -> str:
    if state.get("requires_approval"):
        return "hitl"
    return "generate"


def build_generic_agent():
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("tool", tool_node)
    graph.add_node("generate", generate_node)
    graph.add_node("hitl", hitl_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "retrieve": "retrieve",
            "tool": "tool",
            "generate": "generate"
        }
    )

    graph.add_edge("retrieve", "generate")

    graph.add_conditional_edges(
        "tool",
        route_after_tool,
        {
            "hitl": "hitl",
            "generate": "generate"
        }
    )

    graph.add_edge("hitl", END)
    graph.add_edge("generate", END)

    agent = graph.compile()
    logger.info("Generic agent graph compiled")
    return agent


generic_agent = build_generic_agent()