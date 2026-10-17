#!/usr/bin/env python3
"""Score an exported Quant Brain research report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.research_evaluation import evaluate_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="ResearchReport JSON file")
    parser.add_argument("--labels", type=Path, help="Optional independent benchmark labels JSON")
    parser.add_argument("--latency-ms", type=float)
    parser.add_argument("--estimated-cost-usd", type=float)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    labels = json.loads(args.labels.read_text(encoding="utf-8")) if args.labels else None
    scorecard = evaluate_report(
        report,
        labels=labels,
        latency_ms=args.latency_ms,
        estimated_cost_usd=args.estimated_cost_usd,
    )
    print(json.dumps(scorecard, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
