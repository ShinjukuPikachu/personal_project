from __future__ import annotations
from pathlib import Path
from claude_agent_sdk import AgentDefinition

def _load_runbook(name: str) -> str:
    return (Path(__file__).parent.parent.parent / "runbooks" / f"{name}.md").read_text()

_OUTPUT_CONTRACT = """

## Your task

You receive a structured list of commits for this release. Each commit shows: short_hash, type, scope, whether it is breaking, subject, Jira tickets (key + status + type), PR number, and CI results.

Classify each commit with an audience tier:
- "internal" — chore, ci, build, docs, internal-only fixes, refactors
- "customer" — user-visible fixes, new features, performance improvements, breaking changes
- "marketing" — major new capabilities, enterprise integrations, significant performance milestones

Then write the Internal Announcement (all-staff Slack/email).

Return ONE JSON object only — no prose, no markdown fences:
{
  "commits": [
    {
      "short_hash": "a1b2c3d",
      "commit_type": "feat",
      "scope": "picking",
      "is_breaking": false,
      "audience": "customer",
      "reason": "New user-visible capability in picking module"
    }
  ],
  "internal_announcement": "## MujinOS v2.3.0 Released\\n\\n..."
}

Include ALL commits from the input in the output commits array.
"""

CLASSIFIER_AGENT = AgentDefinition(
    description="Classify commits by audience and write internal announcement",
    prompt=_load_runbook("product-manager") + _OUTPUT_CONTRACT,
    tools=[],
    model="sonnet",
)
