"""Provider wrapper: anthropic | bedrock | none (SPEC §9).

complete() returns a string or None. Any error, timeout, or provider "none"
returns None so the app is always demoable offline.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

from .config import get_config

log = logging.getLogger(__name__)


def complete(system: str, user: str) -> Optional[str]:
    cfg = get_config()
    provider = cfg.llm.provider
    if provider == "none":
        return None
    try:
        if provider == "anthropic":
            return _anthropic(system, user, cfg)
        if provider == "bedrock":
            return _bedrock(system, user, cfg)
        log.warning("Unknown LLM provider %s", provider)
        return None
    except Exception as exc:  # pragma: no cover - network/credentials
        log.warning("LLM call failed (%s); falling back", exc)
        return None


def _anthropic(system: str, user: str, cfg) -> Optional[str]:  # pragma: no cover
    import anthropic

    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        timeout=cfg.llm.timeout_s,
    )
    msg = client.messages.create(
        model=cfg.llm.model,
        max_tokens=cfg.llm.max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in msg.content if block.type == "text")


def _bedrock(system: str, user: str, cfg) -> Optional[str]:  # pragma: no cover
    import boto3

    client = boto3.client("bedrock-runtime")
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": cfg.llm.max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": [{"type": "text", "text": user}]}],
    }
    resp = client.invoke_model(modelId=cfg.llm.model, body=json.dumps(body))
    payload = json.loads(resp["body"].read())
    return "".join(b.get("text", "") for b in payload.get("content", []))
