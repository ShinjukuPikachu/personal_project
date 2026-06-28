# release-pilot for Claude

Show-and-tell project for Nyanko Release Engineer (DevEx) interview. Demonstrates AI-assisted release automation via multi-agent orchestration.

## Quick Start

```bash
# Setup
pip install -r requirements.txt
cp .env.example .env

# Run (all 3 in separate terminals)
python mcp_server.py                    # Mock MCP server
TEST_DATA=1 uvicorn api:app --port 8080  # API service
python slackbot.py                      # Slackbot
```

Then trigger in Slack: `/release v2.3.0`

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | required | Claude API key |
| `SLACK_BOT_TOKEN` | required | Slack bot token (xoxb-...) |
| `SLACK_APP_TOKEN` | required | Slack app token (xapp-...) |
| `SLACK_CHANNEL` | C0BDFHM8EA2 | Default channel for release posts |
| `TEST_DATA` | (unset) | Set to `1` for mock mode (routes calls to test_data/) |
| `DB_PATH` | ./releases.db | SQLite database path |

## Agent Pipeline

Three-phase async coordinator in `release_pilot/coordinator.py`:

- **Phase 0**: `jira_enrichment` + `github_enrichment` (MCP tools fetch Jira & GitHub context)
- **Phase 1**: `classifier` + `readiness` agents (parallel classification and readiness scoring)
- **Phase 2**: `customer_notes`, `marketing_notes`, `breaking_change` agents (parallel content generation)

Each agent loads a system prompt from `runbooks/<agent>.md`.

## Key Files

| File | Purpose |
|------|---------|
| `api.py` | FastAPI + Strawberry GraphQL service |
| `slackbot.py` | Slack Socket Mode listener |
| `mcp_server.py` | Mock MCP server (local development) |
| `release_pilot/coordinator.py` | 3-phase agent orchestrator |
| `runbooks/` | Agent system prompts (markdown persona files) |
| `test_data/` | Mock JSON fixtures for TEST_DATA=1 mode |

## Tuning Agent Behavior

Edit `runbooks/<agent>.md` files to adjust tone, detail level, or focus without modifying code. Agents load these at runtime.

## Test Data

`TEST_DATA=1` mode:
- Uses 12 mock NyankoOS v2.3.0 commits (test_data/commits.json)
- PR #46 has 2 intentionally failing CI checks (demonstrates readiness scoring)
- No external API calls; all responses from test_data/*.json

## Run Tests

```bash
pytest tests/ -v
```
