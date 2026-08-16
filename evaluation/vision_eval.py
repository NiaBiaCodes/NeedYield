#!/usr/bin/env python3
"""Evaluate saved vision predictions without making or fabricating predictions."""
import argparse
import json
from pathlib import Path


def normalize(label: str) -> str:
    value = label.strip().lower()
    return {"tomatoes": "tomato", "cucumbers": "cucumber", "peppers": "pepper", "carrots": "carrot", "herbs": "herb"}.get(value, value)


def evaluate(cases: list[dict]) -> dict:
    classified = [case for case in cases if case.get("expected_label") and case.get("predicted_label")]
    quantities = [case for case in cases if case.get("actual_quantity") is not None and case.get("predicted_quantity") is not None]
    accuracy = sum(normalize(case["expected_label"]) == normalize(case["predicted_label"]) for case in classified) / len(classified) if classified else None
    mae = sum(abs(float(case["actual_quantity"]) - float(case["predicted_quantity"])) for case in quantities) / len(quantities) if quantities else None
    return {"total_cases": len(cases), "classification_cases": len(classified), "classification_accuracy": accuracy, "quantity_cases": len(quantities), "quantity_mae": mae}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate NeedYield produce recognition labels and quantities.")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("vision_test_cases.json"))
    args = parser.parse_args()
    payload = json.loads(args.cases.read_text())
    cases = payload["cases"] if isinstance(payload, dict) else payload
    result = evaluate(cases)
    print(json.dumps(result, indent=2))
    if not cases:
        print("No labeled vision cases are present. Metrics are intentionally null; add real human-labeled images before reporting performance.")


if __name__ == "__main__":
    main()
