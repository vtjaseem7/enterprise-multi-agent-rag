from typing import TypedDict


class AgentState(TypedDict):
    query: str
    tenant_id: str
    user_role: str
    user_groups: list[str]
    route: str
    retrieved_chunks: list[dict]
    analysis: str
    answer: str
    citations: list[str]