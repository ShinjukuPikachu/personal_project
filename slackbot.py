#!/usr/bin/env python3
"""Release Pilot Slackbot — receives /release slash commands via Socket Mode."""
from __future__ import annotations
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

import httpx
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")
SERVICE_URL = os.environ.get("SERVICE_URL", "http://localhost:30080/graphql")

if not SLACK_BOT_TOKEN:
    print("ERROR: SLACK_BOT_TOKEN not set. Copy .env.example to .env and fill in your tokens.")
    sys.exit(1)
if not SLACK_APP_TOKEN:
    print("ERROR: SLACK_APP_TOKEN not set. Copy .env.example to .env and fill in your tokens.")
    sys.exit(1)

app = App(token=SLACK_BOT_TOKEN)

TRIGGER_RELEASE = """
mutation TriggerRelease($input: ReleaseInputGQL!) {
  triggerRelease(input: $input) {
    jobId
    status
  }
}
"""

@app.command("/release")
def handle_release(ack, command, client, logger):
    ack()  # must respond within 3 seconds

    version = command.get("text", "").strip()
    channel = command.get("channel_id", "")
    user = command.get("user_id", "")

    # Validate version format
    if not version:
        client.chat_postMessage(
            channel=channel,
            text="Usage: `/release v2.3.0`  — please include a version string.",
        )
        return
    if not version.startswith("v"):
        client.chat_postMessage(
            channel=channel,
            text=f"⚠️ Invalid version `{version}` — must start with `v` (e.g. `v2.3.0`).",
        )
        return

    # Post immediate acknowledgment and capture ts for threading
    ack_resp = client.chat_postMessage(
        channel=channel,
        text=f"⏳ Generating release notes for *{version}*... (triggered by <@{user}>)",
    )
    thread_ts = ack_resp["ts"]

    # Call the GraphQL service
    try:
        resp = httpx.post(
            SERVICE_URL,
            json={
                "query": TRIGGER_RELEASE,
                "variables": {
                    "input": {
                        "version": version,
                        "fromRef": "auto",
                        "channel": channel,
                        "threadTs": thread_ts,
                    }
                },
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

        if "errors" in data:
            raise ValueError(f"GraphQL errors: {data['errors']}")

        job_id = data["data"]["triggerRelease"]["jobId"]
        logger.info(f"Release job started: {job_id} for {version}")

    except httpx.ConnectError:
        client.chat_postMessage(
            channel=channel,
            text=f"❌ Could not reach release service at `{SERVICE_URL}`. Is it running? Try: `uvicorn api:app --port 8080`",
        )
    except Exception as e:
        logger.error(f"Failed to trigger release {version}: {e}")
        client.chat_postMessage(
            channel=channel,
            text=f"❌ Failed to trigger release `{version}`: {e}",
        )


if __name__ == "__main__":
    print("⚡ Release Pilot Slackbot connecting via Socket Mode...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
