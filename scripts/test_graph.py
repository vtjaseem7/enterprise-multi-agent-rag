from app.graph.workflow import rag_graph


def ask(query: str, role: str) -> None:
    print(f"\n================ {role.upper()} ASKS: {query} ================")
    result = rag_graph.invoke({
        "query": query,
        "tenant_id": "tenant_acme",
        "user_role": role,
        "user_groups": [],
        "route": "",
        "retrieved_chunks": [],
        "analysis": "",
        "answer": "",
        "citations": [],
    })
    print("\nAnswer:\n", result["answer"])
    print("Citations:", result["citations"])


def main() -> None:
    # 1. Simple lookup (should take Fast Path: router -> retrieve -> respond)
    ask("What is the solution for error AUTH-401?", role="customer")

    # 2. Complex investigation by Customer (should be blocked by ACL)
    ask("Investigate why API 500 errors spiked after release v2.4.", role="customer")

    # 3. Complex investigation by Admin (should take Investigation Path: router -> retrieve -> analyze -> respond)
    ask("Investigate why API 500 errors spiked after release v2.4.", role="admin")


if __name__ == "__main__":
    main()