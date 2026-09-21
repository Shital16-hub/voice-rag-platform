from typing import TypedDict, Optional


class AgentState(TypedDict):
    """
    Everything the agent remembers during one conversation turn.
    Flows through every node in the graph.
    """
    question: str
    user_id: str
    tenant_id: str
    agent_id: str
    system_prompt: str
    tools_enabled: list[str]
    mcp_servers: list[dict]
    retrieved_chunks: list[dict]
    route: str
    tool_name: Optional[str]
    tool_input: Optional[dict]
    tool_result: Optional[dict]
    requires_approval: bool
    approval_status: Optional[str]
    answer: Optional[str]
    error: Optional[str]