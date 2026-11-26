import json
import time
from pathlib import Path
from app.graph.workflow import rag_graph

GOLDEN_PATH = Path("data/evaluation/golden_set.json")


def run_evaluation() -> None:
    cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    passed = 0

    print(f"\nRunning {len(cases)} Golden Evaluation Cases...\n")
    print(f"{'ID':<10} {'Route':<10} {'Source OK':<12} {'Facts OK':<10} {'Latency':<10} {'Status'}")
    print("-" * 68)

    for case in cases:
        start = time.perf_counter()
        result = rag_graph.invoke({
            "query": case["query"],
            "tenant_id": "tenant_acme",
            "user_role": case["role"],
            "user_groups": [],
            "route": "",
            "retrieved_chunks": [],
            "analysis": "",
            "answer": "",
            "citations": [],
        })
        elapsed = round(time.perf_counter() - start, 2)


        expected_source = case["expected_source"]
        if expected_source is None:
            source_ok = len(result["citations"]) == 0
        else:
            source_ok = expected_source in result["citations"]


        answer_normalized = " ".join(result["answer"].split()).lower()
        facts_ok = all(term.lower() in answer_normalized for term in case["must_contain"])


        case_passed = source_ok and facts_ok
        if case_passed:
            passed += 1

        status = "PASS" if case_passed else "FAIL"
        print(
            f"{case['id']:<10} {result['route']:<10} {str(source_ok):<12} "
            f"{str(facts_ok):<10} {elapsed:<10}s {status}"
        )
        if not case_passed:
            print(f"  -> Answer was: {result['answer']}")

    score = round((passed / len(cases)) * 100, 1)
    print("-" * 68)
    print(f"Final Score: {passed}/{len(cases)} passed ({score}%)\n")


if __name__ == "__main__":
    run_evaluation()