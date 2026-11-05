"""Run via: python -m tools.qa_postdeploy.cli --base-url ... --environment ..."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .models import RunConfig, Verdict
from .runner import run_postdeploy_checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="148AI read-only post-deployment verifier")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--project-id")
    parser.add_argument("--expected-sha")
    parser.add_argument("--trusted-observed-sha", help="Only from trusted deployment/CI metadata, NEVER app content")
    parser.add_argument("--allowed-host", action="append", default=[], help="Exact authorized HTTPS hostname; repeatable")
    parser.add_argument("--token-env-var", default="QA_BEARER_TOKEN")
    parser.add_argument("--json-output")
    parser.add_argument("--mode", default="SAFE", choices=("SAFE", "CANARY"))
    args = parser.parse_args(argv)
    if args.mode != "SAFE":
        print("Configuration error: CANARY not implemented", file=sys.stderr)
        return 3
    if not args.token_env_var.isidentifier():
        print("Configuration error: invalid token variable name", file=sys.stderr)
        return 3
    try:
        result = run_postdeploy_checks(RunConfig(
            base_url=args.base_url, target_environment=args.environment,
            project_id=args.project_id, bearer_token=os.getenv(args.token_env_var),
            expected_commit_sha=args.expected_sha, trusted_observed_commit_sha=args.trusted_observed_sha,
            allowed_hosts=tuple(args.allowed_host),
        ))
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 3
    for check in result.checks:
        print(f"{check.status.value:8} {check.check_id:20} {check.classification.value:29} {check.evidence_summary}")
    print(f"VERDICT: {result.verdict.value}")
    if args.json_output:
        target = Path(args.json_output)
        data = json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n"
        if len(data.encode("utf-8")) > 1_000_000:
            print("Evidence exceeds output size limit", file=sys.stderr)
            return 3
        try:
            target.write_text(data, encoding="utf-8")
        except OSError:
            print("Could not write output file", file=sys.stderr)
            return 3
    return 0 if result.verdict == Verdict.VERIFIED else (1 if result.verdict == Verdict.FAILED else 2)


if __name__ == "__main__":
    sys.exit(main())
