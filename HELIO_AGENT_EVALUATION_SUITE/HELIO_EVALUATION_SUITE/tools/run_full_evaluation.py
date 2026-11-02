#!/usr/bin/env python3
"""Orchestrate HELIO evaluation: agent suites + UI API acceptance + scoring + human review files.

Honest about simulator mode and missing AI judge credentials.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
REPORTS = ROOT / "reports"


def run(cmd, cwd=None, env=None):
    print("+", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=cwd or ROOT, env=env, text=True)
    if p.returncode != 0:
        raise SystemExit(f"Command failed ({p.returncode}): {' '.join(cmd)}")


def load_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def save_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows),
        encoding="utf-8",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=dt.datetime.now(dt.timezone.utc).strftime("run_%Y%m%dT%H%M%SZ"))
    ap.add_argument("--include-legacy", action="store_true")
    ap.add_argument("--skip-agent", action="store_true")
    ap.add_argument("--skip-ui", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="Limit agent cases per suite file (debug)")
    ap.add_argument("--judge-provider", default="none", choices=["none", "bedrock", "openai_compatible"])
    ap.add_argument("--judge-model", default=None)
    args = ap.parse_args()

    out_dir = REPORTS / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(TOOLS) + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("HELIO_AGENT_API_URL", "http://127.0.0.1:8001")
    env.setdefault("HELIO_WEB_URL", "http://127.0.0.1:3000")

    # 1) Suite integrity
    run([sys.executable, str(TOOLS / "validate_suite.py")], env=env)
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, env=env)

    all_responses = []
    if not args.skip_agent:
        # Single deduped agent case file (exclude ui_e2e; optionally include legacy).
        all_cases = load_jsonl(ROOT / "cases/public/ALL_CASES.jsonl")
        agent_cases = [
            c
            for c in all_cases
            if c.get("suite") != "ui_e2e"
            and (args.include_legacy or c.get("suite") != "legacy_exploratory")
        ]
        # Prefer CORE order first for early signal, then the rest.
        core_ids = {c["case_id"] for c in load_jsonl(ROOT / "cases/public/CORE_REGRESSION.jsonl")}
        ordered = [c for c in agent_cases if c["case_id"] in core_ids] + [
            c for c in agent_cases if c["case_id"] not in core_ids
        ]
        cases_path = out_dir / "agent_cases_selected.jsonl"
        save_jsonl(cases_path, ordered)
        dest = out_dir / "responses.jsonl"
        cmd = [
            sys.executable,
            str(TOOLS / "run_agent.py"),
            "--adapter",
            "helio_adapter:invoke_case",
            "--cases",
            str(cases_path),
            "--out",
            str(dest),
        ]
        if args.limit:
            cmd += ["--limit", str(args.limit)]
        print("+", " ".join(cmd), flush=True)
        p = subprocess.run(cmd, cwd=ROOT, env=env, text=True)
        all_responses = load_jsonl(dest)
        for r in all_responses:
            if r.get("turn_results"):
                rc = r["turn_results"][0].get("run_config")
                if rc and "run_config" not in r:
                    r["run_config"] = rc
        save_jsonl(dest, all_responses)
        print(
            f"agent cases: {len(all_responses)} responses (adapter_exit={p.returncode})",
            flush=True,
        )

    # 2) UI acceptance
    ui_rows = []
    if not args.skip_ui:
        ui_out = out_dir / "ui_api_results.jsonl"
        run([sys.executable, str(TOOLS / "run_ui_api_acceptance.py"), "--out", str(ui_out)], env=env)
        ui_rows = load_jsonl(ui_out)

    # 3) Score agent responses (trace gates; AI judge optional)
    grades = []
    summary = {}
    if all_responses:
        score_dir = out_dir / "scored"
        cmd = [
            sys.executable,
            str(TOOLS / "score_responses.py"),
            "--responses",
            str(out_dir / "responses.jsonl"),
            "--provider",
            args.judge_provider,
            "--out-dir",
            str(score_dir),
        ]
        if args.judge_provider != "none":
            if not args.judge_model:
                raise SystemExit("--judge-model required when judge-provider != none")
            cmd += ["--model", args.judge_model]
        if args.include_legacy:
            cmd.append("--include-legacy")
        print("+", " ".join(cmd), flush=True)
        subprocess.run(cmd, cwd=ROOT, env=env, text=True)
        grades = load_jsonl(score_dir / "grades.jsonl")
        if (score_dir / "summary.json").exists():
            summary = json.loads((score_dir / "summary.json").read_text(encoding="utf-8"))

    # 4) Build unified per-test results for human review
    public = {r["case_id"]: r for r in load_jsonl(ROOT / "cases/public/ALL_CASES.jsonl")}
    grade_by = {g["case_id"]: g for g in grades}
    resp_by = {r["case_id"]: r for r in all_responses}
    ui_by = {r["case_id"]: r for r in ui_rows}

    unified = []
    for case_id, case in sorted(public.items()):
        row = {
            "case_id": case_id,
            "suite": case.get("suite"),
            "category": case.get("category"),
            "title": case.get("title"),
            "tenant_id": case.get("tenant_id"),
            "actor": case.get("actor"),
            "risk": case.get("risk"),
        }
        if case.get("suite") == "ui_e2e":
            ui = ui_by.get(case_id)
            if not ui:
                row.update({"status": "NOT_RUN", "detail": "UI harness did not execute this case"})
            else:
                row.update(
                    {
                        "status": ui.get("status"),
                        "elapsed_ms": ui.get("elapsed_ms"),
                        "http_status": ui.get("http_status"),
                        "evidence": ui.get("evidence"),
                        "detail": ui.get("detail"),
                    }
                )
        else:
            g = grade_by.get(case_id)
            r = resp_by.get(case_id)
            if not r and not g:
                row.update({"status": "NOT_RUN", "detail": "Agent suite not executed for this case in this run"})
            else:
                turns = (r or {}).get("turn_results") or []
                row.update(
                    {
                        "status": (g or {}).get("status") or "EXECUTED_UNSCORED",
                        "semantic_score": (g or {}).get("semantic_score"),
                        "judge_error": (g or {}).get("judge_error"),
                        "trace_check": (g or {}).get("trace_check"),
                        "run_config": (r or {}).get("run_config")
                        or (turns[0].get("run_config") if turns else None),
                        "turn_count": len(turns),
                        "answers": [t.get("answer") for t in turns],
                        "run_ids": [t.get("run_id") for t in turns if t.get("run_id")],
                        "tool_event_counts": [len(t.get("tool_events") or []) for t in turns],
                        "verified_effects": [t.get("verified_effects") for t in turns],
                        "state_assertions": [t.get("state_assertions") for t in turns],
                        "turn_errors": [t.get("error") for t in turns if t.get("error")],
                    }
                )
        unified.append(row)

    save_jsonl(out_dir / "ALL_TEST_RESULTS.jsonl", unified)

    # Markdown report
    counts = collections.Counter(r.get("status") or "UNKNOWN" for r in unified)
    by_suite = {
        s: dict(collections.Counter(r["status"] for r in unified if r.get("suite") == s))
        for s in sorted({r.get("suite") for r in unified})
    }
    mode_note = "simulator (MODEL_PROVIDER=simulator; Bedrock not configured for this run)"
    md = [
        f"# HELIO Full Evaluation Results — `{args.run_id}`",
        "",
        f"- Generated (UTC): {dt.datetime.now(dt.timezone.utc).isoformat()}",
        f"- Agent mode: **{mode_note}**",
        f"- Judge: `{args.judge_provider}` / `{args.judge_model or 'n/a'}`",
        f"- Agent API: `{env.get('HELIO_AGENT_API_URL')}`",
        f"- Cases in unified file: {len(unified)}",
        f"- Agent responses captured: {len(all_responses)}",
        f"- UI cases executed: {len(ui_rows)}",
        "",
        "## Status counts (all suites)",
        "",
    ]
    for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        md.append(f"- **{k}**: {v}")
    md += ["", "## By suite", ""]
    for s, c in by_suite.items():
        md.append(f"### {s}")
        for k, v in sorted(c.items()):
            md.append(f"- {k}: {v}")
        md.append("")

    md += [
        "## Important interpretation notes",
        "",
        "- This run used the **offline simulator** agent path (real tool calls to enterprise mock APIs). It is **workflow simulation**, not LLM accuracy.",
        "- With `--judge-provider none`, semantic answer quality is marked `NEEDS_AI_JUDGE` unless hard safety vetoes fire.",
        "- `PASS_VERIFIED` requires AI judge + trusted server evidence; do not treat `NEEDS_AI_JUDGE` as a pass.",
        "- Legacy exploratory cases are informational unless `--include-legacy` was set and oracles curated.",
        "- UI browser-only cases may be `SKIPPED_UNSUPPORTED` without Playwright.",
        "",
        "## Per-case results",
        "",
        "| case_id | suite | status | title |",
        "|---|---|---|---|",
    ]
    for r in unified:
        title = (r.get("title") or "").replace("|", "/")
        md.append(f"| {r['case_id']} | {r.get('suite')} | {r.get('status')} | {title} |")

    md += [
        "",
        "## Files in this run directory",
        "",
        "- `ALL_TEST_RESULTS.jsonl` — one JSON object per case (use this for your own review)",
        "- `ALL_TEST_RESULTS.md` — this report",
        "- `responses.jsonl` — raw agent adapter observations",
        "- `ui_api_results.jsonl` — UI/API acceptance outcomes",
        "- `scored/grades.jsonl`, `scored/summary.json`, `scored/report.md`, `scored/review_bundle.jsonl`",
        "",
    ]
    (out_dir / "ALL_TEST_RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # Copy convenience pointers at reports/
    (REPORTS / "LATEST_RUN.txt").write_text(str(out_dir) + "\n", encoding="utf-8")
    # Also write a project-root convenience copy for the user
    workspace = ROOT.parents[1] if (ROOT.parents[1] / "compose.yaml").exists() else ROOT.parents[1]
    user_copy = workspace / "EVALUATION_RESULTS"
    user_copy.mkdir(parents=True, exist_ok=True)
    for name in ("ALL_TEST_RESULTS.md", "ALL_TEST_RESULTS.jsonl"):
        src = out_dir / name
        if src.exists():
            (user_copy / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    meta = {
        "run_id": args.run_id,
        "out_dir": str(out_dir),
        "status_counts": dict(counts),
        "by_suite": by_suite,
        "agent_responses": len(all_responses),
        "ui_cases": len(ui_rows),
        "judge_provider": args.judge_provider,
        "agent_mode": "simulator",
        "scored_summary": summary,
    }
    (user_copy / "SUMMARY.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (out_dir / "SUMMARY.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print("\n=== EVAL COMPLETE ===")
    print("Run dir:", out_dir)
    print("User copy:", user_copy)
    print("Status counts:", dict(counts))


if __name__ == "__main__":
    main()
