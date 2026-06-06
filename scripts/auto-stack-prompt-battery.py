#!/usr/bin/env python3
"""Comprehensive Auto (Local LLMs) routing battery.

Layer A: direct local_llm_router routing (tier/model/reasons).
Layer B: Odysseus /api/chat_stream integration (model_info, model_resolved, errors).

Writes:
  scripts/auto-stack-battery-results.json
  scripts/auto-stack-battery-report.md
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "odysseus")
ROUTER_SRC = os.path.join(os.path.dirname(ROOT), "local-llm-router", "src")
RESULTS_PATH = os.path.join(ROOT, "scripts", "auto-stack-battery-results.json")
REPORT_PATH = os.path.join(ROOT, "scripts", "auto-stack-battery-report.md")

DEFAULT_POOL = ["gemma4:e4b", "qwen3:8b", "qwen3:14b"]
OLLAMA_TAGS = os.environ.get("OLLAMA_TAGS_URL", "http://127.0.0.1:11434/api/tags")
ODYSSEUS_BASE = os.environ.get("ODYSSEUS_BASE", "http://127.0.0.1:7000")
STREAM_TIMEOUT = float(os.environ.get("BATTERY_STREAM_TIMEOUT", "12"))
ITERATION = int(os.environ.get("BATTERY_ITERATION", "1"))


@dataclass
class PromptCase:
    id: str
    category: str
    prompt: str
    mode: str = "chat"  # chat | agent
    expect_tiers: tuple[str, ...] = ()
    expect_code_model: bool | None = None  # True/False/None=don't check
    notes: str = ""


@dataclass
class LayerAResult:
    id: str
    category: str
    mode: str
    tier: str
    model: str
    reasons: list[str]
    ok: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class LayerBResult:
    id: str
    category: str
    mode: str
    ok: bool
    events: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""


def _http_json(url: str, *, method: str = "GET", data: dict | None = None, timeout: float = 10) -> Any:
    body = None
    headers = {"Accept": "application/json"}
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw.strip() else {}


def fetch_ollama_models() -> list[str]:
    try:
        tags = _http_json(OLLAMA_TAGS, timeout=5)
        models = sorted({m["name"] for m in tags.get("models", []) if m.get("name")})
        return models
    except Exception:
        return []


def build_pool(installed: list[str]) -> list[str]:
    if len(installed) >= 2:
        desired = DEFAULT_POOL
        pool = [m for m in desired if m in installed]
        if len(pool) >= 2:
            return pool
        return installed[: max(2, len(installed))]
    return list(DEFAULT_POOL)


def prompt_battery() -> list[PromptCase]:
    long_arch = (
        "Design a fault-tolerant microservices architecture for a real-time analytics platform "
        "that ingests millions of events per minute from heterogeneous sources, applies stream "
        "processing with exactly-once semantics, stores hot data in a columnar warehouse, and "
        "serves sub-second dashboards globally. Explain tradeoffs between Kafka vs Pulsar, "
        "event sourcing vs CRUD, and how you would handle backpressure, schema evolution, "
        "multi-region failover, and observability without blowing up operational cost."
    )
    md_heavy = (
        "# API Notes\n\n"
        "## Auth\n"
        "- JWT bearer tokens\n"
        "- refresh via `/oauth/token`\n\n"
        "## Errors\n"
        "| code | meaning |\n"
        "| 401 | unauthorized |\n"
        "| 429 | rate limit |\n\n"
        "Summarize the auth flow in one sentence."
    )
    cases = [
        # Simple
        PromptCase("s01", "simple", "hi", expect_tiers=("simple",)),
        PromptCase("s02", "simple", "what is 2+2", expect_tiers=("simple",)),
        PromptCase("s03", "simple", "thanks!", expect_tiers=("simple",)),
        PromptCase("s04", "simple", "ok", expect_tiers=("simple",)),
        PromptCase("s05", "simple", "ping", expect_tiers=("simple",)),
        # Medium
        PromptCase("m01", "medium", "summarize JWT in one paragraph", expect_tiers=("medium", "simple")),
        PromptCase("m02", "medium", "explain how DNS works briefly", expect_tiers=("medium", "simple")),
        PromptCase("m03", "medium", "compare REST vs GraphQL", expect_tiers=("medium", "simple")),
        PromptCase("m04", "medium", "outline a plan for learning Rust", expect_tiers=("medium", "simple")),
        PromptCase("m05", "medium", "what is JWT?", mode="chat", expect_tiers=("simple", "medium")),
        # Code
        PromptCase(
            "c01", "code",
            "write a python function to merge two sorted lists",
            expect_tiers=("complex", "medium"),
            expect_code_model=True,
        ),
        PromptCase(
            "c02", "code",
            "implement a binary search function in python with unit tests",
            expect_tiers=("complex", "medium"),
            expect_code_model=True,
        ),
        PromptCase(
            "c03", "code",
            "refactor this auth module for testability ```python def login(u,p): pass```",
            expect_tiers=("complex", "medium"),
            expect_code_model=True,
        ),
        PromptCase(
            "c04", "code",
            "debug this traceback: SyntaxError on line 12",
            expect_tiers=("complex", "medium"),
            expect_code_model=True,
        ),
        # Shell
        PromptCase(
            "sh01", "shell",
            "run ls -la and explain the output",
            mode="agent",
            expect_tiers=("complex",),
            expect_code_model=True,
        ),
        PromptCase(
            "sh02", "shell",
            "use bash to list files in the project root",
            mode="agent",
            expect_tiers=("complex",),
            expect_code_model=True,
        ),
        PromptCase(
            "sh03", "shell",
            "execute git status and summarize",
            mode="agent",
            expect_tiers=("complex",),
            expect_code_model=True,
        ),
        PromptCase(
            "sh04", "shell",
            "run pip list and tell me if requests is installed",
            mode="agent",
            expect_tiers=("complex",),
            expect_code_model=True,
        ),
        # Long / complex
        PromptCase("l01", "long", long_arch, mode="agent", expect_tiers=("complex", "reasoning")),
        PromptCase(
            "l02", "long",
            long_arch,
            mode="chat",
            expect_tiers=("medium", "complex", "reasoning"),
            notes="chat mode may cap architecture to medium unless shell/code",
        ),
        PromptCase(
            "l03", "long",
            "prove step by step why quicksort average case is O(n log n)",
            mode="agent",
            expect_tiers=("reasoning", "complex"),
            notes="reasoning markers; chat mode caps reasoning tier to medium",
        ),
        # Agent-style
        PromptCase(
            "a01", "agent",
            "create a todo for tomorrow",
            mode="agent",
            expect_tiers=("medium", "complex", "simple"),
        ),
        PromptCase(
            "a02", "agent",
            "remind me to call the dentist next Tuesday",
            mode="agent",
            expect_tiers=("medium", "complex", "simple"),
        ),
        PromptCase(
            "a03", "agent",
            "Reply with exactly: pong",
            mode="agent",
            expect_tiers=("simple",),
        ),
        PromptCase(
            "a04", "agent",
            "Reply with exactly: pong",
            mode="chat",
            expect_tiers=("simple",),
        ),
        # Edge
        PromptCase("e01", "edge", "   ", expect_tiers=("simple",)),
        PromptCase("e02", "edge", "🙂🚀✨", expect_tiers=("simple", "medium")),
        PromptCase("e03", "edge", md_heavy, expect_tiers=("medium", "simple")),
        PromptCase("e04", "edge", "???", expect_tiers=("simple",)),
        PromptCase("e05", "edge", "yes", expect_tiers=("simple",)),
    ]
    return cases


def load_router():
    for path in (ROUTER_SRC, APP):
        if path not in sys.path:
            sys.path.insert(0, path)
    import local_llm_router as router  # noqa: E402

    reset = getattr(router, "reset_session_for_tests", None)
    if callable(reset):
        reset()
    else:
        from local_llm_router.session import reset_session_for_tests  # noqa: E402

        reset_session_for_tests()
    return router


def run_layer_a(cases: list[PromptCase], pool: list[str]) -> list[LayerAResult]:
    router = load_router()
    router.configure(vram_gb=16, quant="qat", models=pool)
    tiers = router.get_session().tiers
    has_code_slot = bool(tiers.code)

    results: list[LayerAResult] = []
    for case in cases:
        decision = router.explain(case.prompt, mode=case.mode)
        tier = decision.tier.value if hasattr(decision.tier, "value") else str(decision.tier)
        model = decision.model
        reasons = list(decision.reasons)
        issues: list[str] = []

        if case.expect_tiers and tier not in case.expect_tiers:
            issues.append(f"tier {tier!r} not in expected {case.expect_tiers}")
        if case.expect_code_model is True and has_code_slot:
            if model != tiers.code:
                issues.append(f"expected code model {tiers.code!r}, got {model!r}")
        elif case.expect_code_model is True and not has_code_slot:
            if tier not in ("complex", "medium"):
                issues.append(f"code-like prompt tier {tier!r} below medium without code slot")
        if case.expect_code_model is False and has_code_slot and model == tiers.code:
            issues.append(f"unexpected code model {model!r}")
        if case.mode and not any(f"mode={case.mode}" in r for r in reasons):
            issues.append(f"reasons missing mode={case.mode}")

        results.append(
            LayerAResult(
                id=case.id,
                category=case.category,
                mode=case.mode,
                tier=tier,
                model=model,
                reasons=reasons,
                ok=not issues,
                issues=issues,
            )
        )
    return results


def odysseus_reachable() -> tuple[bool, str]:
    for path in ("/api/sessions", "/"):
        try:
            req = urllib.request.Request(f"{ODYSSEUS_BASE}{path}", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status < 500:
                    return True, f"HTTP {resp.status} on {path}"
        except Exception as exc:
            last = str(exc)
    return False, last


def get_local_endpoint() -> dict | None:
    eps = None
    for path in ("/api/model-endpoints", "/api/endpoints"):
        try:
            eps = _http_json(f"{ODYSSEUS_BASE}{path}", timeout=8)
            if isinstance(eps, list):
                break
        except Exception:
            eps = None
    if not isinstance(eps, list):
        return None
    for ep in eps:
        if not ep.get("is_enabled", True):
            continue
        base = (ep.get("base_url") or "").lower()
        kind = ep.get("endpoint_kind") or ""
        if "11434" in base or kind == "local":
            return ep
    return eps[0] if eps else None


def create_auto_stack_session(endpoint: dict) -> str | None:
    sid = str(uuid.uuid4())
    data = {
        "name": f"battery-{sid[:8]}",
        "endpoint_id": endpoint.get("id", ""),
        "model": "__auto_stack__",
        "skip_validation": "true",
    }
    try:
        out = _http_json(f"{ODYSSEUS_BASE}/api/session", method="POST", data=data, timeout=15)
        return out.get("id") or sid
    except Exception:
        return None


def parse_sse(raw: str) -> list[dict]:
    events: list[dict] = []
    for block in re.split(r"\n\n+", raw):
        if not block.strip() or block.strip().startswith(":"):
            continue
        data_line = None
        event_type = None
        for line in block.splitlines():
            if line.startswith("data: "):
                data_line = line[6:]
            elif line.startswith("event: "):
                event_type = line[7:].strip()
        if data_line is None:
            continue
        if data_line == "[DONE]":
            events.append({"type": "done"})
            continue
        try:
            payload = json.loads(data_line)
        except json.JSONDecodeError:
            payload = {"raw": data_line}
        if event_type == "error":
            payload = {"type": "error", "error": payload}
        elif "type" not in payload:
            if "delta" in payload:
                payload["type"] = "delta"
            elif event_type:
                payload["type"] = event_type
        events.append(payload)
    return events


def stream_chat(session_id: str, message: str, mode: str) -> tuple[list[dict], list[str]]:
    data = {
        "message": message,
        "session": session_id,
        "mode": mode,
        "allow_bash": "true" if mode == "agent" else "false",
        "allow_web_search": "false",
        "incognito": "true",
    }
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        f"{ODYSSEUS_BASE}/api/chat_stream",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    chunks: list[str] = []
    errors: list[str] = []
    try:
        with urllib.request.urlopen(req, timeout=STREAM_TIMEOUT) as resp:
            start = time.time()
            while True:
                line = resp.readline().decode("utf-8", errors="replace")
                if not line:
                    break
                chunks.append(line)
                if time.time() - start > STREAM_TIMEOUT:
                    break
                if "data: [DONE]" in line:
                    break
    except urllib.error.HTTPError as exc:
        errors.append(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}")
    except Exception as exc:
        errors.append(str(exc))
    return parse_sse("".join(chunks)), errors


def run_layer_b(cases: list[PromptCase]) -> tuple[list[LayerBResult], dict[str, Any]]:
    meta: dict[str, Any] = {"odysseus_base": ODYSSEUS_BASE}
    ok, detail = odysseus_reachable()
    meta["server_reachable"] = ok
    meta["server_detail"] = detail
    if not ok:
        return [
            LayerBResult(
                id=c.id,
                category=c.category,
                mode=c.mode,
                ok=False,
                skipped=True,
                skip_reason=f"Odysseus unreachable: {detail}",
            )
            for c in cases
        ], meta

    endpoint = get_local_endpoint()
    meta["endpoint"] = endpoint
    if not endpoint:
        return [
            LayerBResult(
                id=c.id,
                category=c.category,
                mode=c.mode,
                ok=False,
                skipped=True,
                skip_reason="No enabled ModelEndpoint found",
            )
            for c in cases
        ], meta

    session_id = create_auto_stack_session(endpoint)
    meta["session_id"] = session_id
    if not session_id:
        return [
            LayerBResult(
                id=c.id,
                category=c.category,
                mode=c.mode,
                ok=False,
                skipped=True,
                skip_reason="Failed to create __auto_stack__ session",
            )
            for c in cases
        ], meta

    # Subset: representative prompts per category + both modes
    subset_ids = {
        "s01", "s02", "m01", "m05", "c01", "sh01", "l01", "l02", "a01", "a03", "a04", "e01", "e02",
    }
    subset = [c for c in cases if c.id in subset_ids]

    results: list[LayerBResult] = []
    for case in subset:
        events, transport_errors = stream_chat(session_id, case.prompt, case.mode)
        issues: list[str] = []
        summary: dict[str, Any] = {
            "model_info": None,
            "model_resolved": [],
            "errors": [],
            "auto_stack_errors": [],
            "has_delta": False,
        }

        for ev in events:
            et = ev.get("type")
            if et == "model_info":
                summary["model_info"] = ev
                if not ev.get("auto_stack") and ev.get("requested_model") == "__auto_stack__":
                    issues.append("model_info missing auto_stack flag")
                if ev.get("model") in ("", "__auto_stack__", None):
                    issues.append(f"model_info.model not resolved: {ev.get('model')!r}")
            elif et == "model_resolved":
                summary["model_resolved"].append(ev)
            elif et == "error":
                summary["errors"].append(ev)
                issues.append(f"SSE error: {ev}")
            elif et == "delta":
                text = str(ev.get("delta", ""))
                summary["has_delta"] = summary["has_delta"] or bool(text.strip())
                if "UnboundLocalError" in text:
                    issues.append("UnboundLocalError in stream delta")
                if "Auto (Local LLMs):" in text and "needs" in text.lower():
                    summary["auto_stack_errors"].append(text[:240])
            elif et == "done":
                pass

        for err in transport_errors:
            issues.append(err)
            if "404" in err and "auto_name" in err.lower():
                issues.append("404 on auto_name path")

        # Routing-layer pass: got model_info with a real model before timeout/model-down
        routing_ok = bool(summary["model_info"] and summary["model_info"].get("model"))
        if case.mode == "agent" and not summary["model_resolved"] and routing_ok:
            # Agent may still be prepping; not a hard fail if model_info present
            pass
        if summary["auto_stack_errors"] and not summary["has_delta"]:
            issues.append(f"auto_stack error without content: {summary['auto_stack_errors'][0][:120]}")

        hard_fail_markers = ("UnboundLocalError", "auto_name", "404")
        for issue in issues:
            if any(m in issue for m in hard_fail_markers):
                routing_ok = False

        results.append(
            LayerBResult(
                id=case.id,
                category=case.category,
                mode=case.mode,
                ok=routing_ok and not any("UnboundLocalError" in i for i in issues),
                events=summary,
                errors=transport_errors,
                issues=issues,
            )
        )
        time.sleep(0.3)
    return results, meta


def summarize_layer_a(results: list[LayerAResult]) -> dict[str, Any]:
    passed = sum(1 for r in results if r.ok)
    by_cat: dict[str, dict[str, int]] = {}
    for r in results:
        bucket = by_cat.setdefault(r.category, {"pass": 0, "fail": 0})
        if r.ok:
            bucket["pass"] += 1
        else:
            bucket["fail"] += 1
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "by_category": by_cat,
    }


def summarize_layer_b(results: list[LayerBResult]) -> dict[str, Any]:
    ran = [r for r in results if not r.skipped]
    passed = sum(1 for r in ran if r.ok)
    skipped = sum(1 for r in results if r.skipped)
    return {
        "total": len(results),
        "ran": len(ran),
        "passed": passed,
        "failed": len(ran) - passed,
        "skipped": skipped,
    }


def write_report(
    *,
    pool: list[str],
    layer_a: list[LayerAResult],
    layer_b: list[LayerBResult],
    meta_b: dict[str, Any],
    iteration: int,
    fixes: list[str],
) -> None:
    sa = summarize_layer_a(layer_a)
    sb = summarize_layer_b(layer_b)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Auto Stack Routing Battery Report",
        "",
        f"Generated: {now}  |  Iteration: {iteration}",
        "",
        "## Summary",
        "",
        f"- **Layer A (router):** {sa['passed']}/{sa['total']} passed",
        f"- **Layer B (Odysseus):** {sb['passed']}/{sb['ran']} passed ({sb['skipped']} skipped)",
        f"- **Model pool:** `{', '.join(pool)}`",
        "",
    ]
    if fixes:
        lines += ["## Fixes applied this run", ""] + [f"- {f}" for f in fixes] + [""]

    lines += ["## Layer A failures", ""]
    fail_a = [r for r in layer_a if not r.ok]
    if not fail_a:
        lines.append("_None_")
    else:
        for r in fail_a:
            lines.append(f"- **{r.id}** ({r.category}, mode={r.mode}): tier={r.tier}, model={r.model}")
            for issue in r.issues:
                lines.append(f"  - {issue}")
    lines.append("")

    lines += ["## Layer B results", ""]
    if meta_b.get("server_reachable") is False:
        lines.append(f"_Odysseus unreachable: {meta_b.get('server_detail')}_")
    elif not layer_b:
        lines.append("_No integration cases run_")
    else:
        for r in layer_b:
            status = "SKIP" if r.skipped else ("PASS" if r.ok else "FAIL")
            lines.append(f"- **{r.id}** [{status}] mode={r.mode}")
            if r.skipped:
                lines.append(f"  - {r.skip_reason}")
                continue
            mi = r.events.get("model_info") or {}
            lines.append(
                f"  - model_info: tier={mi.get('tier')}, model={mi.get('model')}, "
                f"reasons={mi.get('route_reasons', [])[:2]}"
            )
            if r.events.get("model_resolved"):
                mr = r.events["model_resolved"][0]
                lines.append(f"  - model_resolved: tier={mr.get('tier')}, model={mr.get('model')}")
            if r.issues:
                for issue in r.issues:
                    lines.append(f"  - issue: {issue}")
    lines.append("")

    lines += [
        "## Layer A detail (tier → model)",
        "",
        "| id | category | mode | tier | model | ok |",
        "|---|---|---|---|---|---|",
    ]
    for r in layer_a:
        lines.append(f"| {r.id} | {r.category} | {r.mode} | {r.tier} | {r.model} | {'✓' if r.ok else '✗'} |")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    cases = prompt_battery()
    installed = fetch_ollama_models()
    pool = build_pool(installed)

    layer_a = run_layer_a(cases, pool)
    layer_b, meta_b = run_layer_b(cases)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pool": pool,
        "installed_ollama": installed,
        "layer_a": [asdict(r) for r in layer_a],
        "layer_b": [asdict(r) for r in layer_b],
        "layer_a_summary": summarize_layer_a(layer_a),
        "layer_b_summary": summarize_layer_b(layer_b),
        "layer_b_meta": meta_b,
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    write_report(pool=pool, layer_a=layer_a, layer_b=layer_b, meta_b=meta_b, iteration=ITERATION, fixes=[])
    sa = payload["layer_a_summary"]
    sb = payload["layer_b_summary"]
    print(f"Layer A: {sa['passed']}/{sa['total']} passed")
    print(f"Layer B: {sb['passed']}/{sb['ran']} passed ({sb['skipped']} skipped)")
    print(f"Results: {RESULTS_PATH}")
    print(f"Report:  {REPORT_PATH}")
    return 0 if sa["failed"] == 0 and sb["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
