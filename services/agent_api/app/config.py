"""Application configuration."""
import os
from pathlib import Path

# Model provider
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "simulator")  # simulator|bedrock|ollama
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
BEDROCK_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

# Demo time
DEMO_NOW = os.getenv("DEMO_NOW", "2026-10-31T10:00:00Z")

# Session security
SESSION_SIGNING_KEY = os.getenv("APP_SESSION_SIGNING_KEY", "dev-only-insecure-key-change-in-production")
SESSION_COOKIE_NAME = "helio_session"
SESSION_MAX_AGE = 86400  # 24 hours

# Database
APP_DB_PATH = Path(os.getenv("APP_DB_PATH", "/data/app.sqlite"))

# Enterprise API
ENTERPRISE_API_URL = os.getenv("ENTERPRISE_API_URL", "http://enterprise-mock-api:8000")

# Reset confirmation
CONFIRM_RESET_DEMO = os.getenv("CONFIRM_RESET_DEMO", "")

# Evaluation mode
EVAL_MODE = int(os.getenv("EVAL_MODE", "0"))

# Limits
MAX_TOOL_CALLS_PER_RUN = int(os.getenv("MAX_TOOL_CALLS_PER_RUN", "25"))
MAX_RUN_DURATION_SECONDS = int(os.getenv("MAX_RUN_DURATION_SECONDS", "120"))
MAX_PROMPT_TOKENS = int(os.getenv("MAX_PROMPT_TOKENS", "50000"))
