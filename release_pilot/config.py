import os
from pathlib import Path

SLACK_CHANNEL: str = os.environ.get("SLACK_CHANNEL", "C0BDFHM8EA2")
DB_PATH: str = os.environ.get("DB_PATH", "./releases.db")
TEST_DATA: bool = os.environ.get("TEST_DATA", "0") == "1"
TEST_DATA_DIR: Path = Path(os.environ.get("TEST_DATA_DIR", "./test_data"))
ANTHROPIC_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")
KIMI_API_KEY: str | None = os.environ.get("KIMI_API_KEY")
KIMI_BASE_URL: str = os.environ.get("KIMI_BASE_URL", "https://api.moonshot.ai/v1")
KIMI_MODEL: str = os.environ.get("KIMI_MODEL", "moonshot-v1-8k")
WEB_BASE_URL: str = os.environ.get("WEB_BASE_URL", "http://localhost:30080")
PDF_DIR: str = os.environ.get("PDF_DIR", "./data/pdfs")
SLACK_BOT_TOKEN: str | None = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN: str | None = os.environ.get("SLACK_APP_TOKEN")
