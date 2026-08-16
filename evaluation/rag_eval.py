#!/usr/bin/env python3
"""Evaluate Chroma retrieval only; generated Gemini prose is not scored."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / "backend" / ".env")

from app.services.rag_service import rag_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate NeedYield RAG retrieval with labeled resource IDs.")
    parser.add_argument("--questions", type=Path, default=Path(__file__).with_name("rag_test_questions.json"))
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    cases = json.loads(args.questions.read_text())
    if not cases:
        raise SystemExit("No labeled RAG questions found.")

    hits_at_1 = 0
    hits_at_k = 0
    recalls = []
    details = []
    modes = set()
    for case in cases:
        documents, mode = rag_service._retrieve(case["question"], count=max(3, args.k))
        modes.add(mode)
        retrieved = [document.metadata["resource_id"] for document in documents]
        expected = set(case["expected_resource_ids"])
        top_k = retrieved[:args.k]
        hit_1 = bool(retrieved and retrieved[0] in expected)
        hit_k = bool(expected.intersection(top_k))
        recall = len(expected.intersection(top_k)) / len(expected) if expected else 0.0
        hits_at_1 += hit_1; hits_at_k += hit_k; recalls.append(recall)
        details.append({"question": case["question"], "expected": sorted(expected), "retrieved_top_k": top_k, "hit_at_1": hit_1, f"hit_at_{args.k}": hit_k, f"recall_at_{args.k}": recall})

    result = {
        "question_count": len(cases), "retrieval_modes": sorted(modes),
        "hit_rate_at_1": hits_at_1 / len(cases), f"hit_rate_at_{args.k}": hits_at_k / len(cases),
        f"mean_recall_at_{args.k}": sum(recalls) / len(recalls), "details": details,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
