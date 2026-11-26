from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.cache import get_cached_response, set_cached_response
from app.core.security import CurrentUser, get_current_user
from app.graph.workflow import rag_graph

router = APIRouter(prefix="/api/v1", tags=["Chat"])


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000)


class ChatResponse(BaseModel):
    route: str
    answer: str
    citations: list[str]
    cached: bool = False


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:
    """Check Redis cache first; if missed, run LangGraph and cache the result."""
    cached_data = get_cached_response(
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        user_groups=current_user.access_groups,
        query=request.query,
    )
    if cached_data:
        print("[Cache] HIT - returning cached answer (0 LLM tokens used)")
        return ChatResponse(**cached_data, cached=True)


    print("[Cache] MISS - running LangGraph workflow")
    result = rag_graph.invoke({
        "query": request.query,
        "tenant_id": current_user.tenant_id,
        "user_role": current_user.role,
        "user_groups": current_user.access_groups,
        "route": "",
        "retrieved_chunks": [],
        "analysis": "",
        "answer": "",
        "citations": [],
    })

    response_payload = {
        "route": result["route"],
        "answer": result["answer"],
        "citations": result["citations"],
    }

    set_cached_response(
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        user_groups=current_user.access_groups,
        query=request.query,
        data=response_payload,
    )

    return ChatResponse(**response_payload, cached=False)