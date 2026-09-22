"""All tunable knobs in one place."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GROUND_TRUTH = ROOT / "ground_truth"
FIXTURES = ROOT / "fixtures"
RUNS = ROOT / "runs"

# The demo runs "as of" this date. The corpus is built around it.
AS_OF = "2026-09-21"
OWNER = "Puja Sridhar"
OWNER_EMAIL = "puja@example.com"

# Verified against strands-agents 1.56.0: AnthropicConfig takes model_id + max_tokens.
MODEL_ID = "claude-sonnet-5"
MAX_TOKENS = 4096

# Bright Data MCP is a node process launched over stdio.
BRIGHTDATA_MCP_CMD = "npx"
BRIGHTDATA_MCP_ARGS = ["-y", "@brightdata/mcp"]

COGNEE_DATASET = "second_guess"

# A commitment counts as AT_RISK if its due date lands on a day the owner is
# unavailable, or within this many days of one.
AT_RISK_BUFFER_DAYS = 0

# Verdicts. Deterministic Python owns these - never the model.
OK = "OK"
AT_RISK = "AT_RISK"
BROKEN = "BROKEN"
