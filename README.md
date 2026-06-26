# release-pilot

AI-powered release notes generation for MujinOS.

## What It Does

- **Slack integration**: Receive `/release v2.3.0` command via Slack, triggering automated release notes generation
- **AI-powered pipeline**: Coordinate 7 AI agents across 3 parallel phases to classify commits, score readiness, and generate release notes
- **Multi-channel delivery**: Post internal announcements, customer-facing notes, marketing summaries, and traceability matrices to Slack

## Architecture

```
/release v2.3.0  →  slackbot.py (Socket Mode)
                        │ POST /graphql
                        ▼
               api.py (FastAPI + Strawberry GraphQL, K8s :30080)
                        │
                        ▼
              coordinator.py (3-phase async pipeline)
                Phase 0 ──── jira_enrichment + github_enrichment (MCP tools)
                Phase 1 ──── classifier + readiness (parallel)
                Phase 2 ──── customer_notes + marketing_notes + breaking (parallel)
                        │
                        ▼
               Slack: 📢 Announcement | 📋 Customer Notes | 📣 Marketing | 🔍 Release Plan (thread)
```

## Quick Start (Local, No K8s)

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in ANTHROPIC_API_KEY, SLACK_BOT_TOKEN, SLACK_APP_TOKEN

# Terminal 1: mock MCP server
python mcp_server.py

# Terminal 2: API service  
TEST_DATA=1 uvicorn api:app --port 8080

# Terminal 3: Slackbot
python slackbot.py

# Then in Slack: /release v2.3.0
```

## Production Deployment

```bash
bash setup.sh  # Deploy to K8s (fill in k8s/secret.yaml first)
```

## Development

- **GraphQL Playground**: http://localhost:8080/graphql (local) or http://localhost:30080/graphql (K8s)
- **Run tests**: `pytest tests/ -v`
- **Agent behavior**: Edit runbooks/ markdown files to tune behavior without code changes
- **Test data mode**: `TEST_DATA=1` routes calls to mock data in test_data/ (12 MujinOS v2.3.0 commits with intentional CI failures)
