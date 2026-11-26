from app.ingestion.pipeline import ingest_file
from app.retrieval.retriever import hybrid_search


def main() -> None:

    print("Ingesting internal_postmortem.txt (admin-only)...")
    ingest_file(
        file_path="data/raw/internal_postmortem.txt",
        tenant_id="tenant_acme",
        allowed_roles=["admin"],
        allowed_groups=["engineering"],
        category="incident_reports",
    )

    print("\n--- Test A: Customer asking about AUTH-401 ---")
    res_a = hybrid_search(
        query="What is the solution for error AUTH-401?",
        tenant_id="tenant_acme",
        user_role="customer",
    )
    for r in res_a:
        print(f"[{r['source']}] (score={r['rerank_score']}): {r['text'][:120]}...")



    print("\n--- Test B: Customer asking about internal v2.4 postmortem ---")
    res_b = hybrid_search(
        query="Why did API 500 errors spike after release v2.4?",
        tenant_id="tenant_acme",
        user_role="customer",
    )
    print(f"Results returned for customer: {len(res_b)}")
    for r in res_b:
        print(f"  - {r['source']} (notice internal_postmortem.txt is NOT here!)")



    print("\n--- Test C: Admin asking about internal v2.4 postmortem ---")
    res_c = hybrid_search(
        query="Why did API 500 errors spike after release v2.4?",
        tenant_id="tenant_acme",
        user_role="admin",
    )
    for r in res_c:
        print(f"[{r['source']}] (score={r['rerank_score']}): {r['text'][:120]}...")


if __name__ == "__main__":
    main()