"""Client for the optional local LLM (Ollama). Returns None whenever the LLM is
off or fails, so callers always have a non-LLM path."""
from __future__ import annotations

import json
import logging
import re

import httpx

from ..config import settings
from .model_manager import model_manager

log = logging.getLogger("anvaya.llm")
_JSON_OBJECT = re.compile(r"\{.*\}", re.S)


def _parse_json(text: str) -> dict | None:
    text = (text or "").strip()
    for candidate in (text, (_JSON_OBJECT.search(text) or [None])[0] if _JSON_OBJECT.search(text) else None):
        if not candidate:
            continue
        try:
            value = json.loads(candidate)
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            continue
    return None


class OllamaClient:
    def __init__(self) -> None:
        self._http = httpx.Client(base_url=settings.ollama_url or "http://localhost", timeout=settings.llm_timeout)
        self.calls = 0

    @property
    def available(self) -> bool:
        return model_manager.llm_ok

    def chat_json(self, system: str, user: str, schema: dict, num_predict: int = 160) -> dict | None:
        if not self.available:
            return None
        self.calls += 1
        try:
            resp = self._http.post("/api/chat", json={
                "model": settings.llm_model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "stream": False, "format": schema, "keep_alive": "24h",
                "options": {"temperature": 0, "num_ctx": settings.llm_num_ctx, "num_predict": num_predict},
            })
            resp.raise_for_status()
            return _parse_json(resp.json().get("message", {}).get("content", ""))
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM call failed: %s", exc)
            return None
