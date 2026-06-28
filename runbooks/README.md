# Runbooks — Agent System Prompts

Each `.md` file here is the system prompt (persona) for one AI agent in the pipeline.
Agents load these files **at runtime** — editing a runbook changes agent behavior without any code changes or redeployment.

## How Agents Load Runbooks

```python
def _load_runbook(name: str) -> str:
    return (Path(__file__).parent.parent.parent / "runbooks" / f"{name}.md").read_text()

READINESS_AGENT = AgentDefinition(
    prompt=_load_runbook("release-manager") + "\n\n" + READINESS_OUTPUT_CONTRACT,
    ...
)
```

## Active Runbooks

| File | Agent(s) | Purpose |
|------|----------|---------|
| `product-manager.md` | classifier, customer_notes, marketing_notes | Commit classification, customer + marketing copy |
| `release-manager.md` | readiness, breaking_change | Go/no-go scoring, rollback plans |
| `qa-manager.md` | readiness | CI analysis, regression risk per commit |

## Demo: Swapping Personas

The following alternate runbooks are ready to swap in for live demos.
Each swap takes ~5 seconds. Run the same `/release vX.X.X` command before and after to show the difference.

### PM Persona A → Enterprise / Compliance-first (`product-manager-enterprise.md`)

Produces **formal, structured** customer notes with mandatory `[Action required]` labels.
Breaking changes appear at the top in a dedicated "Required Actions" section. Reads like a
change-management notification, not a product announcement.

```bash
cp runbooks/product-manager.md runbooks/product-manager-balanced.md   # save original
cp runbooks/product-manager-enterprise.md runbooks/product-manager.md # swap in
# trigger /release in Slack → customer notes will be formal, structured
cp runbooks/product-manager-balanced.md runbooks/product-manager.md   # restore
```

### PM Persona B → Concise / Startup (`product-manager-concise.md`)

Produces **terse, metric-first** bullet notes. One line per change. No paragraphs.
Reads like a GitHub release tag body — scannable in under 60 seconds.

```bash
cp runbooks/product-manager.md runbooks/product-manager-balanced.md
cp runbooks/product-manager-concise.md runbooks/product-manager.md
# trigger /release in Slack → customer notes will be short bullets with numbers
cp runbooks/product-manager-balanced.md runbooks/product-manager.md
```

### Release Manager → Strict / Zero-Tolerance (`release-manager-strict.md`)

Raises the READY threshold from **80 → 90**, applies steeper penalties, and auto-BLOCKs
on any CI failure on customer-facing commits. The same release that scored READY under
the default rules will typically become HOLD or BLOCKED.

```bash
cp runbooks/release-manager.md runbooks/release-manager-balanced.md
cp runbooks/release-manager-strict.md runbooks/release-manager.md
# trigger /release in Slack → watch the readiness badge change from READY to HOLD/BLOCKED
cp runbooks/release-manager-balanced.md runbooks/release-manager.md
```

## What the Demo Shows

| Point | How to show it |
|-------|---------------|
| No code change needed | Swap the `.md` file, re-trigger the same version — output is different |
| Different teams own their runbook | "Security wrote the strict RM runbook; marketing wrote the PM runbook" |
| Auditable | `git log runbooks/product-manager.md` shows when a tone decision changed |
| LLM-agnostic | The runbook is plain English — it works with Kimi, Anthropic, or any model |
| Tunable without engineers | A PM or compliance officer can edit these files directly |
