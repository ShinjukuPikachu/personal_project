from __future__ import annotations
import asyncio
import json
import re
from release_pilot.models import (
    ChangeSet, ReleaseResult, ReadinessReport, TraceabilityRow, JiraTicket, CIStatus
)
from release_pilot.agents.jira_enrichment_agent import JIRA_ENRICHMENT_AGENT
from release_pilot.agents.github_enrichment_agent import GITHUB_ENRICHMENT_AGENT
from release_pilot.agents.classifier_agent import CLASSIFIER_AGENT
from release_pilot.agents.readiness_agent import READINESS_AGENT
from release_pilot.agents.customer_notes_agent import CUSTOMER_NOTES_AGENT
from release_pilot.agents.marketing_notes_agent import MARKETING_NOTES_AGENT
from release_pilot.agents.breaking_change_agent import BREAKING_CHANGE_AGENT

import anthropic as _anthropic
from release_pilot.agents.base import AgentDefinition
from release_pilot import config as _config


async def run(changeset: ChangeSet) -> ReleaseResult:
    """Three-phase async pipeline. Phase 0: MCP enrichment. Phase 1: classify + readiness. Phase 2: notes."""
    if _config.TEST_DATA:
        return _load_test_result(changeset)

    # ── Phase 0: MCP enrichment (parallel) ────────────────────────────────
    all_jira_keys = list({k for c in changeset.commits for k in c.jira_keys})
    all_shas = [c.hash for c in changeset.commits]

    jira_result, github_result = await asyncio.gather(
        _run_agent(JIRA_ENRICHMENT_AGENT, json.dumps({"jira_keys": all_jira_keys})),
        _run_agent(GITHUB_ENRICHMENT_AGENT, json.dumps({"commit_shas": all_shas})),
    )

    # Merge enrichment into commits
    enriched = _merge_enrichment(changeset, jira_result, github_result)

    # ── Phase 1: classify + readiness (parallel) ──────────────────────────
    classify_input = _build_classify_input(enriched)
    readiness_input = _build_readiness_input(enriched)

    classify_result, readiness_result = await asyncio.gather(
        _run_agent(CLASSIFIER_AGENT, classify_input),
        _run_agent(READINESS_AGENT, readiness_input),
    )

    # Apply classifier audience labels to commits
    audience_map = {c["short_hash"]: c["audience"] for c in classify_result.get("commits", [])}
    for commit in enriched.commits:
        commit.audience = audience_map.get(commit.short_hash, "internal")

    # ── Phase 2: notes generation (parallel) ──────────────────────────────
    customer_commits = [c for c in enriched.commits if c.audience in ("customer", "marketing")]
    marketing_commits = [c for c in enriched.commits if c.audience == "marketing"]

    phase2_coros = [
        _run_agent(CUSTOMER_NOTES_AGENT, _build_notes_input(customer_commits, enriched.version, "customer")),
        _run_agent(MARKETING_NOTES_AGENT, _build_notes_input(marketing_commits, enriched.version, "marketing")),
    ]
    if enriched.breaking:
        phase2_coros.append(_run_agent(BREAKING_CHANGE_AGENT, _build_breaking_input(enriched.breaking)))

    phase2_results = await asyncio.gather(*phase2_coros)
    customer_result = phase2_results[0]
    marketing_result = phase2_results[1]
    breaking_result = phase2_results[2] if len(phase2_results) > 2 else None

    # ── Build final result ─────────────────────────────────────────────────
    return _build_release_result(enriched, classify_result, readiness_result,
                                  customer_result, marketing_result, breaking_result)


def _load_test_result(changeset: ChangeSet) -> ReleaseResult:
    """Return a fully pre-baked ReleaseResult from test_data/release_result.json."""
    data = json.loads((_config.TEST_DATA_DIR / "release_result.json").read_text())
    classify = data["classify"]
    readiness_data = data["readiness"]
    jira_data = json.loads((_config.TEST_DATA_DIR / "jira_issues.json").read_text())
    github_prs = json.loads((_config.TEST_DATA_DIR / "github_prs.json").read_text())
    github_ci = json.loads((_config.TEST_DATA_DIR / "github_check_runs.json").read_text())

    audience_map = {c["short_hash"]: c["audience"] for c in classify["commits"]}
    traceability = []
    for commit in changeset.commits:
        commit.audience = audience_map.get(commit.short_hash, "internal")
        jira_tickets = []
        for key in commit.jira_keys:
            issue = jira_data.get("issues", {}).get(key, {})
            if issue and "error" not in issue:
                jira_tickets.append(JiraTicket(
                    key=issue.get("key", key),
                    summary=issue.get("summary", ""),
                    status=issue.get("status", "Unknown"),
                    issue_type=issue.get("issue_type", "Unknown"),
                    priority=issue.get("priority"),
                ))
        pr = github_prs.get("prs", {}).get(commit.hash, {})
        ci = github_ci.get("check_runs", {}).get(commit.hash, {})
        ci_status = CIStatus(
            total=ci.get("total", 0),
            passed=ci.get("passed", 0),
            failed=ci.get("failed", 0),
            failed_names=ci.get("failed_names", []),
        ) if ci.get("total", 0) > 0 else None
        traceability.append(TraceabilityRow(
            short_hash=commit.short_hash,
            description=commit.clean_subject,
            commit_type=commit.commit_type,
            is_breaking=commit.is_breaking,
            jira_tickets=jira_tickets,
            pr_number=pr.get("number") if pr else None,
            pr_url=pr.get("url") if pr else None,
            ci_status=ci_status,
        ))

    return ReleaseResult(
        version=changeset.version,
        suggested_bump=changeset.suggested_bump,
        readiness=ReadinessReport(
            score=readiness_data["score"],
            recommendation=readiness_data["recommendation"],
            rationale=readiness_data["rationale"],
            risk_factors=readiness_data["risk_factors"],
            rollback_plan=readiness_data["rollback_plan"],
        ),
        internal_announcement=classify["internal_announcement"],
        customer_notes=data["customer_notes"]["customer_notes"],
        marketing_notes=data["marketing_notes"]["marketing_notes"],
        traceability=traceability,
    )


def _merge_enrichment(changeset: ChangeSet, jira_result: dict, github_result: dict) -> ChangeSet:
    """Attach Jira tickets and GitHub PR/CI data to each commit."""
    jira_issues = jira_result.get("issues", {})
    prs = github_result.get("prs", {})
    check_runs = github_result.get("check_runs", {})

    for commit in changeset.commits:
        # Jira tickets
        commit.jira_tickets = []
        for key in commit.jira_keys:
            issue = jira_issues.get(key, {})
            if issue and "error" not in issue:
                commit.jira_tickets.append(JiraTicket(
                    key=issue.get("key", key),
                    summary=issue.get("summary", ""),
                    status=issue.get("status", "Unknown"),
                    issue_type=issue.get("issue_type", "Unknown"),
                    priority=issue.get("priority"),
                ))

        # GitHub PR
        pr = prs.get(commit.hash, {})
        if pr and pr.get("number") is not None:
            commit.pr_number = pr.get("number")
            commit.pr_url = pr.get("url")
            commit.pr_title = pr.get("title")

        # CI status
        ci = check_runs.get(commit.hash, {})
        if ci and ci.get("total", 0) > 0:
            commit.ci_status = CIStatus(
                total=ci.get("total", 0),
                passed=ci.get("passed", 0),
                failed=ci.get("failed", 0),
                failed_names=ci.get("failed_names", []),
            )

    changeset.breaking = [c for c in changeset.commits if c.is_breaking]
    return changeset


def _build_classify_input(changeset: ChangeSet) -> str:
    lines = [f"version: {changeset.version}", "commits:"]
    for c in changeset.commits:
        jira_str = " ".join(f"[{t.key} {t.status} {t.issue_type}]" for t in c.jira_tickets) or "none"
        pr_str = f"#{c.pr_number}" if c.pr_number else "none"
        if c.ci_status:
            ci_str = f"{c.ci_status.passed}/{c.ci_status.total} passed"
            if c.ci_status.failed:
                ci_str += f" (FAILED: {', '.join(c.ci_status.failed_names)})"
        else:
            ci_str = "no CI data"
        breaking_flag = " BREAKING" if c.is_breaking else ""
        scope_str = f"({c.scope})" if c.scope else ""
        lines.append(
            f"  - {c.short_hash} | {c.commit_type}{scope_str}{breaking_flag} | {c.clean_subject}"
        )
        lines.append(f"    jira: {jira_str} | pr: {pr_str} | ci: {ci_str}")
    return "\n".join(lines)


def _build_readiness_input(changeset: ChangeSet) -> str:
    return _build_classify_input(changeset)  # same input shape


def _build_notes_input(commits: list, version: str, audience: str) -> str:
    if not commits:
        return json.dumps({"version": version, "commits": [], "audience": audience})
    return json.dumps({
        "version": version,
        "audience": audience,
        "commits": [
            {
                "short_hash": c.short_hash,
                "type": c.commit_type,
                "scope": c.scope,
                "is_breaking": c.is_breaking,
                "subject": c.clean_subject,
                "breaking_note": c.breaking_note,
                "jira_tickets": [{"key": t.key, "summary": t.summary, "status": t.status} for t in c.jira_tickets],
            }
            for c in commits
        ]
    })


def _build_breaking_input(breaking_commits: list) -> str:
    return json.dumps({
        "breaking_commits": [
            {
                "short_hash": c.short_hash,
                "subject": c.clean_subject,
                "breaking_note": c.breaking_note,
                "scope": c.scope,
            }
            for c in breaking_commits
        ]
    })


def _extract_json(text: str) -> dict:
    """Brace-matching scanner: find the last balanced {...} block in text."""
    start = text.rfind("{")
    if start == -1:
        raise ValueError(f"No JSON object found in agent output: {text[:200]!r}")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError(f"Unbalanced braces in agent output: {text[:200]!r}")


def _validate_output(description: str, result: dict, required_keys: list[str]) -> dict:
    missing = [k for k in required_keys if k not in result]
    if missing:
        raise ValueError(f"Agent '{description}' output missing keys: {missing}")
    return result


async def _run_agent(agent_def: AgentDefinition, user_msg: str) -> dict:
    """Invoke one agent via Anthropic API. Tool-using agents fall back to stubs."""
    if agent_def.tools:
        return _stub_response(agent_def.description)

    client = _anthropic.AsyncAnthropic(api_key=_config.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=agent_def.prompt,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = "".join(block.text for block in response.content if hasattr(block, "text"))
    return _extract_json(raw)


def _stub_response(description: str) -> dict:
    """Fallback stub when SDK not installed — returns plausible empty structure."""
    if "classifier" in description.lower() or "classify" in description.lower():
        return {"commits": [], "internal_announcement": "[SDK not installed — stub output]"}
    if "readiness" in description.lower():
        return {"score": 75, "recommendation": "HOLD", "rationale": "SDK not installed",
                "risk_factors": ["claude_agent_sdk not installed"], "rollback_plan": "N/A",
                "per_commit_risk": []}
    if "customer" in description.lower():
        return {"customer_notes": "[SDK not installed — stub output]"}
    if "marketing" in description.lower():
        return {"marketing_notes": None}
    if "breaking" in description.lower():
        return {"affected_components": [], "severity": "UNKNOWN", "migration_steps": [],
                "customer_action_required": False}
    if "jira" in description.lower():
        return {"issues": {}}
    if "github" in description.lower():
        return {"prs": {}, "check_runs": {}}
    return {}


def _build_release_result(
    enriched: ChangeSet,
    classify_result: dict,
    readiness_result: dict,
    customer_result: dict,
    marketing_result: dict,
    breaking_result: dict | None,
) -> ReleaseResult:
    readiness = ReadinessReport(
        score=readiness_result.get("score", 75),
        recommendation=readiness_result.get("recommendation", "HOLD"),
        rationale=readiness_result.get("rationale", ""),
        risk_factors=readiness_result.get("risk_factors", []),
        rollback_plan=readiness_result.get("rollback_plan", ""),
    )

    traceability = []
    for commit in enriched.commits:
        ci = commit.ci_status
        traceability.append(TraceabilityRow(
            short_hash=commit.short_hash,
            description=commit.clean_subject,
            commit_type=commit.commit_type,
            is_breaking=commit.is_breaking,
            jira_tickets=commit.jira_tickets,
            pr_number=commit.pr_number,
            pr_url=commit.pr_url,
            ci_status=ci,
        ))

    return ReleaseResult(
        version=enriched.version,
        suggested_bump=enriched.suggested_bump,
        readiness=readiness,
        internal_announcement=classify_result.get("internal_announcement", ""),
        customer_notes=customer_result.get("customer_notes", ""),
        marketing_notes=marketing_result.get("marketing_notes"),
        traceability=traceability,
    )
