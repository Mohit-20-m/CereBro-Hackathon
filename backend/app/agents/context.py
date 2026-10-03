"""Services the agents share during one analysis run: the LLM client, the
decision cache, the activity trace and progress reporting."""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.ollama_client import OllamaClient
from ..ml.embeddings import cosine
from ..database.models import AgentCache, Conversation, Message, MessageAnalysis, utcnow


class AgentContext:
    def __init__(self, db: Session, conversation: Conversation) -> None:
        self.db = db
        self.conv = conversation
        self.llm = OllamaClient()
        self.trace: list[dict[str, Any]] = []
        self._cache: dict[tuple[str, str], AgentCache] = {
            (row.kind, row.cache_key): row
            for row in db.scalars(select(AgentCache).where(AgentCache.conversation_id == conversation.id))
        }
        self.fallbacks = 0

    # ---- activity trace (shown on the dashboard) --------------------------
    def log(self, agent: str, text: str) -> None:
        self.trace.append({"agent": agent, "text": text, "t": round(time.time(), 2)})

    def stage(self, name: str) -> None:
        self.conv.analysis_stage = name
        self.db.commit()

    # ---- decision cache ----------------------------------------------------
    def cache_get(self, kind: str, key: str) -> dict | None:
        row = self._cache.get((kind, key))
        return row.value if row else None

    def cache_set(self, kind: str, key: str, value: dict) -> None:
        row = self._cache.get((kind, key))
        if row:
            row.value = value
        else:
            row = AgentCache(conversation_id=self.conv.id, kind=kind, cache_key=key[:255], value=value)
            self.db.add(row)
            self._cache[(kind, key)] = row

    # ---- persistence of per-message analysis --------------------------------
    def save_analyses(self, state: dict, seqs: list[int]) -> None:
        by_seq = {m["seq"]: m for m in state["messages"]}
        for seq in seqs:
            data = state["analyses"].get(seq)
            msg_row = self.db.get(Message, by_seq[seq]["db_id"])
            if not data or msg_row is None:
                continue
            row = msg_row.analysis or MessageAnalysis(message_id=msg_row.id)
            row.language_label = data.get("language_label")
            row.languages = data.get("languages") or []
            row.script = data.get("script")
            row.is_code_mixed = bool(data.get("is_code_mixed"))
            row.normalized_text = data.get("normalized")
            row.intent = data.get("intent")
            row.requires_response = bool(data.get("requires_response"))
            row.topic_done = bool(data.get("topic_done"))
            row.topic_key = data.get("topic_key")
            row.topic_name = data.get("topic_name")
            row.embedding = data.get("embedding")
            row.embed_model = data.get("embed_model")
            row.sources = data.get("sources") or {}
            row.updated_at = utcnow()
            if msg_row.analysis is None:
                msg_row.analysis = row
        self.db.commit()

    # ---- helpers used by several agents ---------------------------------------
    @staticmethod
    def meaning(state: dict, seq: int) -> str:
        a = state["analyses"].get(seq, {})
        return a.get("normalized") or next(m["text"] for m in state["messages"] if m["seq"] == seq)

    @staticmethod
    def similarity(state: dict, a: int, b: int) -> float:
        an = state["analyses"]
        return cosine(an.get(a, {}).get("embedding"), an.get(b, {}).get("embedding"))

    @staticmethod
    def describe(state: dict, seq: int) -> str:
        m = next(m for m in state["messages"] if m["seq"] == seq)
        a = state["analyses"].get(seq, {})
        meaning = a.get("normalized")
        extra = f" (meaning: {meaning})" if meaning and meaning.strip() != m["text"].strip() else ""
        return f"#{seq} {m['sender']}: {m['text']}{extra}"
