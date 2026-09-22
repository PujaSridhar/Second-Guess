"""Shared Strands agent construction.

Verified against strands-agents 1.56.0:
  AnthropicModel(client_args={...}, model_id=..., max_tokens=...)
  Agent(model=..., tools=[...], system_prompt=...)
"""
import ast
import json
import os
import re

from strands import Agent
from strands.models.anthropic import AnthropicModel

from .config import MAX_TOKENS, MODEL_ID


def model():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return AnthropicModel(
        client_args={"api_key": key},
        model_id=MODEL_ID,
        max_tokens=MAX_TOKENS,
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
