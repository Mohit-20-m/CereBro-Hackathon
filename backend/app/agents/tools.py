"""Tools the Investigator agent can call. Each searches the part of the
conversation that comes after the question and returns matching messages."""
from __future__ import annotations

from ..ml.embeddings import cosine, embed_texts
from .context import AgentContext


def _after(state: dict, item: dict) -> list[dict]:
    return [m for m in state["messages"] if m["seq"] > item["q_seq"]]


def _row(state: dict, m: dict, sim: float | None = None) -> dict:
    row = {"seq": m["seq"], "sender": m["sender"], "text": m["text"], "meaning": AgentContext.meaning(state, m["seq"])}
    if sim is not None:
        row["sim"] = round(sim, 2)
    return row


def search_messages(ctx: AgentContext, state: dict, item: dict, arg: str) -> list[dict]:
    words = [w for w in arg.lower().split() if len(w) > 1][:3]
    if not words:
        return []
    hits = []
    for m in _after(state, item):
        hay = f"{m['text']} {AgentContext.meaning(state, m['seq'])}".lower()
        if any(w in hay for w in words):
            hits.append(_row(state, m, AgentContext.similarity(state, item["q_seq"], m["seq"])))
    return hits[:5]


def find_similar(ctx: AgentContext, state: dict, item: dict, arg: str) -> list[dict]:
    query = arg.strip() or AgentContext.meaning(state, item["q_seq"])
    vecs, model = embed_texts([query])
    scored = []
    for m in _after(state, item):
        a = state["analyses"].get(m["seq"], {})
        if a.get("embed_model") == model:
            scored.append((cosine(vecs[0], a.get("embedding")), m))
    scored.sort(key=lambda x: -x[0])
    return [_row(state, m, s) for s, m in scored[:4]]


def get_messages_by_speaker(ctx: AgentContext, state: dict, item: dict, arg: str) -> list[dict]:
    name = arg.strip().lower()
    if not name:
        return []
    hits = [m for m in _after(state, item) if m["sender"].lower().startswith(name) or name in m["sender"].lower()]
    return [_row(state, m, AgentContext.similarity(state, item["q_seq"], m["seq"])) for m in hits[:6]]


def get_messages_after(ctx: AgentContext, state: dict, item: dict, arg: str) -> list[dict]:
    try:
        start = int("".join(ch for ch in arg if ch.isdigit()) or item["q_seq"])
    except ValueError:
        start = item["q_seq"]
    hits = [m for m in state["messages"] if m["seq"] > max(start, item["q_seq"])][:5]
    return [_row(state, m, AgentContext.similarity(state, item["q_seq"], m["seq"])) for m in hits]


TOOLS = {
    "search_messages": search_messages,
    "find_similar": find_similar,
    "get_messages_by_speaker": get_messages_by_speaker,
    "get_messages_after": get_messages_after,
}


def format_observation(rows: list[dict]) -> str:
    if not rows:
        return "   (no matching messages)"
    lines = []
    for r in rows:
        meaning = f" (meaning: {r['meaning']})" if r["meaning"].strip() != r["text"].strip() else ""
        sim = f" [similarity {r['sim']:.2f}]" if "sim" in r else ""
        lines.append(f"   #{r['seq']} {r['sender']}: {r['text']}{meaning}{sim}")
    return "\n".join(lines)
