---
marp: true
theme: default
paginate: true
style: |
  section {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    padding: 48px 60px;
  }
  h1 { color: #1a1a2e; font-size: 2rem; }
  h2 { color: #16213e; font-size: 1.5rem; border-bottom: 3px solid #e94560; padding-bottom: 8px; }
  code { background: #f4f4f4; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; }
  pre { background: #1e1e2e; color: #cdd6f4; padding: 16px; border-radius: 8px; font-size: 0.8em; }
  .columns { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }
  blockquote { border-left: 4px solid #e94560; padding-left: 16px; color: #555; font-style: italic; }
---

# release-pilot 🚀
## AI-Assisted Release Automation

Multi-agent orchestration for NyankoOS release notes, readiness scoring, and deployment sign-off

---

## The Problem

Every release, a release engineer manually:

- Reads through **20–30 commits** across multiple repos
- Checks **Jira** for ticket status and open bugs
- Checks **GitHub** for PR CI failures
- Writes **three versions** of release notes (internal / customer / marketing)
- Scores release readiness and gets manager sign-off
- Posts all of this to Slack

> This takes **2–4 hours per release**. It is repetitive, error-prone, and blocks shipping.

---

## The Solution

```
/release v2.7.11
```

One Slack command triggers a **3-phase AI agent pipeline** that does all of it in ~90 seconds.

- **Reads** Jira tickets, GitHub PRs, and CI check results automatically
- **Classifies** every commit by audience (internal / customer / marketing)
- **Writes** release notes in the right voice for each audience
- **Scores** release readiness with a go/no-go recommendation
- **Posts** everything to Slack in a thread, with a PDF download link

---

## Pipeline Architecture

```
/release v2.7.11
       │
       ▼
Phase 0 ── Enrichment (mocked: Jira + GitHub fixtures)
       │       jira_enrichment ──┐
       │       github_enrichment ─┴── merge context
       │
       ▼
Phase 1 ── Analysis (parallel AI agents)
       │       classifier  → audience tier per commit + internal announcement
       │       readiness   → go/no-go score (0–100) + risk factors
       │
       ▼
Phase 2 ── Content Generation (parallel AI agents)
            customer_notes   → public changelog
            marketing_notes  → headline copy
            breaking_change  → migration guide
```

All phase 1 & 2 agents call **Kimi (Moonshot AI)** via the OpenAI-compatible SDK.

---

## Live Demo: What You See in Slack

```
⏳ Generating release notes for v2.7.11... (triggered by @You)

⚙️  Phase 0 — Loading 24 commits + Jira & GitHub data from test fixtures
🤖  Phase 1 — Running 2 AI agents in parallel via Kimi (moonshot-v1-8k)
     • Classifier: labelling 24 commits by audience & breaking-change status
     • Readiness: scoring release risk from CI failures & open Jira tickets
🤖  Phase 2 — Running 3 AI agents in parallel via Kimi (moonshot-v1-8k)
     • Customer Notes: drafting release notes for 16 customer-facing commits
     • Marketing Notes: writing copy for 1 headline feature
     • Breaking Change: documenting migration steps for 2 breaking commit(s)
✅  All agents complete — compiling results...

📢  Internal Announcement  (PR links, Jira keys, CI failures per commit)
📋  Customer Release Notes (benefit-focused, no internal refs)
📣  Marketing Notes        (headline copy, outcome-first)
🔍  Readiness Score: 72/100 — HOLD

📄  Would you like to generate a PDF?  [ ✅ Yes ]  [ No thanks ]
```

---

## Key Design: Runbooks as Agent Personas

Each AI agent's **personality, priorities, and output format** is a plain markdown file.

```
runbooks/product-manager.md    → classifier, customer_notes, marketing_notes
runbooks/release-manager.md    → readiness scoring (READY / HOLD / BLOCKED)
runbooks/qa-manager.md         → CI regression analysis
```

The persona is passed as the **`system` message** to the LLM:

```python
client.chat.completions.create(
    model="moonshot-v1-8k",
    messages=[
        {"role": "system",  "content": agent_def.prompt},   # ← runbook.md
        {"role": "user",    "content": commit_data_json},   # ← real data
    ]
)
```

> **No code change. No redeployment.** Edit the `.md` file → different output.

---

## Demo: Swapping Personas Live

Same 24 commits. Same pipeline. Different runbook → different output.

| Runbook | Customer Notes Style | Readiness Threshold |
|---------|---------------------|---------------------|
| `product-manager.md` *(default)* | Benefit-focused, narrative | READY ≥ 80 |
| `product-manager-enterprise.md` | Formal, `[Action required]` labels, breaking changes first | READY ≥ 80 |
| `product-manager-concise.md` | Metric-first bullets, one line per change | READY ≥ 80 |
| `release-manager-strict.md` | *(unchanged notes)* | **READY ≥ 90** → same release flips to HOLD |

```bash
# swap in enterprise PM, re-run the same version
cp runbooks/product-manager-enterprise.md runbooks/product-manager.md
# → /release v2.7.11 in Slack
```

---

## Web Server + PDF

All release notes are stored in **SQLite on a PVC** and served at `localhost:30080`.

- `/releases` — index of all releases with readiness badges
- `/releases/v2.7.11` — tabbed view: **📋 Customer · 📣 Marketing · 🔒 Internal**
- `/releases/v2.7.11.md` — raw markdown download
- `/releases/v2.7.11.pdf` — generated PDF (customer + marketing + internal, 3 pages)

PDF is generated on-demand via a Slack button click — no manual export step.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Slack interface** | Slack Bolt (Socket Mode), Block Kit buttons |
| **API** | FastAPI + Strawberry GraphQL |
| **AI agents** | Kimi `moonshot-v1-8k` via OpenAI SDK |
| **Orchestration** | Async Python, 3-phase coordinator |
| **Storage** | SQLite on Kubernetes PVC |
| **PDF** | fpdf2 |
| **Infrastructure** | Docker + k3d (k3s in Docker), Kubernetes manifests |
| **Agent tuning** | Plain markdown runbooks — no code changes |

All test data is local fixtures — **no real Jira or GitHub credentials needed** for the demo.

---

## Summary

> **release-pilot** demonstrates that AI agents can replace the most repetitive parts of release engineering — not by being smarter, but by being *configurable*.

**What the demo proves:**

1. **Multi-agent pipelines work** — parallel agents, each with a clear scope, finish faster and are easier to tune than one big prompt
2. **Runbooks separate concerns** — product, engineering, and compliance teams each own their agent's behavior without touching code
3. **The same infrastructure serves multiple audiences** — Slack for real-time, web for archival, PDF for distribution
4. **Operator control** — any team can change how the AI reasons by editing a markdown file

*Built for the Nyanko Release Engineer (DevEx) interview — June 2026*
