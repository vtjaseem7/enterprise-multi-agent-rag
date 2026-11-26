from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from app.core.config import get_settings
from app.graph.state import AgentState
from app.retrieval.retriever import hybrid_search

settings = get_settings()


def get_fast_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="openai/gpt-oss-20b",
        temperature=0,
    )


def get_smart_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="openai/gpt-oss-120b",
        temperature=0,
    )


def router_node(state: AgentState) -> dict:
    llm = get_fast_llm()
    prompt = (
        "Classify the user's question as either 'simple' (direct fact, limit, or error code lookup) "
        "or 'complex' (root-cause investigation, multi-step analysis, or troubleshooting report). "
        "Reply with ONLY one word: simple or complex."
    )
    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=state["query"]),
    ])
    decision = response.content.strip().lower()
    route = "complex" if "complex" in decision else "simple"
    print(f"[Router] Selected path: {route}")
    return {"route": route}



def retrieve_node(state: AgentState) -> dict:
    raw_results = hybrid_search(
        query=state["query"],
        tenant_id=state["tenant_id"],
        user_role=state["user_role"],
        user_groups=state.get("user_groups") or None,
        top_k=3,
    )
    relevant = [r for r in raw_results if r["rerank_score"] > 0]
    print(f"[Retriever] Kept {len(relevant)} relevant chunk(s) out of {len(raw_results)}")
    return {"retrieved_chunks": relevant}



def analyze_node(state: AgentState) -> dict:
    chunks = state.get("retrieved_chunks", [])
    if not chunks:
        return {"analysis": "No authorized documents were found to investigate this issue."}

    context = "\n\n".join(f"Source: {c['source']}\n{c['text']}" for c in chunks)
    llm = get_smart_llm()
    prompt = (
        "You are a senior technical analyst. Based ONLY on the provided context, "
        "identify the root cause, impact, and recommended fix in bullet points. "
        "Do not invent facts outside the context."
    )
    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {state['query']}"),
    ])
    print("[Analyst] Completed root-cause analysis.")
    return {"analysis": response.content}



def respond_node(state: AgentState) -> dict:
    chunks = state.get("retrieved_chunks", [])
    if not chunks:
        return {
            "answer": "I could not find any authorized documents that answer your question.",
            "citations": [],
        }

    context = "\n\n".join(f"[{c['source']}]\n{c['text']}" for c in chunks)
    analysis_section = f"\n\nTechnical Analysis:\n{state['analysis']}" if state.get("analysis") else ""

    llm = get_smart_llm()
    prompt = (
        "You are an enterprise support assistant. Answer the user's question using ONLY "
        "the provided context. Be clear, concise, and cite the source filename in brackets "
        "(e.g., [auth_guide.txt]). Never reveal or guess information not in the context."
    )
    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=f"Context:\n{context}{analysis_section}\n\nQuestion: {state['query']}"),
    ])

    unique_sources = sorted({c["source"] for c in chunks})
    return {
        "answer": response.content,
        "citations": unique_sources,
    }



def route_after_retrieval(state: AgentState) -> str:
    if state.get("route") == "complex":
        return "analyze"
    return "respond"



def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("router")
    workflow.add_edge("router", "retrieve")
    workflow.add_conditional_edges(
        "retrieve",
        route_after_retrieval,
        {
            "analyze": "analyze",
            "respond": "respond",
        },
    )
    workflow.add_edge("analyze", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile()


rag_graph = build_graph()