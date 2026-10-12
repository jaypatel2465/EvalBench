from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml
from sqlalchemy import desc, select

from app.db.base import SessionLocal
from app.models.entities import EvaluationRun
from app.schemas.domain import GatePolicy
from app.services.evaluation import run_metrics
from app.services.regression import quality_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply the EvalBench CI quality gate.")
    parser.add_argument("--baseline", help="Baseline run ID; defaults to previous completed run")
    parser.add_argument("--current", help="Current run ID; defaults to latest completed run")
    parser.add_argument("--policy", default="configs/regression.yaml")
    parser.add_argument("--output", default="artifacts/quality-gate.json")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as session:
        ids = list(session.scalars(select(EvaluationRun.id).where(EvaluationRun.status == "completed").order_by(desc(EvaluationRun.created_at)).limit(2)).all())
        current = args.current or (ids[0] if ids else None)
        baseline = args.baseline or (ids[1] if len(ids) > 1 else None)
        if not current or not baseline:
            print("EvalBench Quality Gate\nDecision: FAILED\nReason: baseline and current completed runs are required")
            return 2
        config = yaml.safe_load(Path(args.policy).read_text(encoding="utf-8"))
        policy = GatePolicy(pass_rate_drop=config["quality_threshold"]["pass_rate_drop"],
            p95_latency_increase=config["latency_threshold"]["p95_increase"], cost_increase=config["cost_threshold"]["increase"])
        before, after = run_metrics(session, baseline), run_metrics(session, current)
        decision = quality_gate(before, after, policy)
        payload = {"baseline_run_id": baseline, "current_run_id": current, **decision.model_dump()}
        path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("EvalBench Quality Gate")
        print(f"\nPass rate:\nBaseline {before['pass_rate']:.1%}\nCurrent {after['pass_rate']:.1%}")
        print(f"\nDecision:\n{decision.decision.upper()}")
        print("\nReason:\n" + "\n".join(decision.reasons))
        return 0 if decision.decision != "failed" or args.warn_only else 1


if __name__ == "__main__":
    raise SystemExit(main())

