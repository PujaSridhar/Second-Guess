"""Shared Strands agent construction.

Verified against strands-agents 1.56.0:
  OpenAIModel(client_args={"api_key": ...}, model_id=..., params={...})
  Agent(model=..., tools=[...], system_prompt=...)

Strands is provider-agnostic. We use OpenAI because that's the key on hand;
swapping to Anthropic or Bedrock is a one-line change in model().
"""
import ast
import json
import os
import re

from dotenv import load_dotenv
from strands import Agent

from .config import MAX_TOKENS, MODEL_ID, ROOT

load_dotenv(ROOT / ".env")


def model():
    key = os.environ.get("OPENAI_API_KEY", "").strip('"')
    if key:
        from strands.models.openai import OpenAIModel
        return OpenAIModel(
            client_args={"api_key": key},
            model_id=MODEL_ID,
            params={"max_completion_tokens": MAX_TOKENS},
        )
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip('"')
    if key:
        from strands.models.anthropic import AnthropicModel
        return AnthropicModel(
            client_args={"api_key": key},
            model_id="claude-sonnet-5",
            max_tokens=MAX_TOKENS,
        )
    raise RuntimeError(
        "No LLM key. Add OPENAI_API_KEY (or ANTHROPIC_API_KEY) to .env"
    )


def agent(system_prompt, tools=None):
    return Agent(model=model(), tools=tools or [], system_prompt=system_prompt)


def parse_structured(text):
    """Pull JSON out of a model reply.

    Falls back to ast.literal_eval because some providers hand back a Python
    repr rather than JSON. Never exec, never eval.
    """
    if not isinstance(text, str):
        text = str(text)
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1)
    start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
    if start == -1:
        raise ValueError(f"no JSON found in reply: {text[:200]}")
    end = max(text.rfind("}"), text.rfind("]"))
    blob = text[start:end + 1]
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return ast.literal_eval(blob)
