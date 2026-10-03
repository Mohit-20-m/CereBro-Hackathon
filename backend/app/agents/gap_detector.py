"""Agent 5 – Gap Detector.

Consumes the structured signals from the other agents and decides, message by
message, whether each thread has turned into a communication gap. It never
asks the LLM "is there a gap?" – the decision is a transparent weighted score,
so every flag can be explained.

For each thread it replays the conversation prefix by prefix and records a
"stage" whenever the gap type or signals change. The UI uses these stages to
show the gap developing during a replay.
"""
from __future__ import annotations

from ..config import settings
from .context import AgentContext

AGENT = "Gap Detector"

WEIGHTS = {"unanswered": 0.40, "repeated": 0.25, "recurrence": 0.20, "clarification": 0.15}
GAP_LABELS = {
    "UNANSWERED_QUESTION": "Unanswered question",
    "IGNORED_REQUEST": "Ignored request",
    "REPEATED_REQUEST": "Repeated request",
    "CLARIFICATION_LOOP": "Clarification loop",
    "UNRESOLVED_TOPIC": "Unresolved topic",
}


def score(signals: dict) -> float:
    return round(sum(w for k, w in WEIGHTS.items() if signals.get(k)), 2)


def severity(value: float) -> str:
    if value < 0.3:
        return "normal"
    return "possible" if value <= 0.6 else "strong"


def _state_at(state: dict, item: dict, k: int, others: list[int]) -> dict | None:
    q, ans = item["q_seq"], item.get("answer_seq")
    replies = [s for s in others if s <= k and s != ans]
    followups = [f for f in item["followups"] if f["seq"] <= k]
    repeated = bool(followups)
    if not (len(replies) >= settings.min_replies_for_gap or (repeated and replies)):
        return None

    clarification = any(f["role"] == "followup" for f in followups)
    deflections = [d for d in item["deflections"] if d <= k]
    own = {f["seq"] for f in item["followups"]}
    recurrence_seqs = []
    if item.get("topic_key"):
        recurrence_seqs = [
            m["seq"] for m in state["messages"]
            if q < m["seq"] <= k and m["seq"] not in own and m["seq"] != ans
            and state["analyses"].get(m["seq"], {}).get("topic_key") == item["topic_key"]
        ]

    if clarification and len(followups) >= 2:
        gap_type = "CLARIFICATION_LOOP"
    elif repeated:
        gap_type = "REPEATED_REQUEST"
    elif deflections:
        gap_type = "UNRESOLVED_TOPIC"
    elif item.get("intent") == "REQUEST":
        gap_type = "IGNORED_REQUEST"
    else:
        gap_type = "UNANSWERED_QUESTION"

    signals = {
        "unanswered": True,
        "repeated": repeated,
        "recurrence": bool(recurrence_seqs),
        "clarification": clarification,
    }
    facts = {
        "replies": len(replies),
        "followups": followups,
        "deflections": deflections,
        "recurrence": recurrence_seqs,
    }
    return {"type": gap_type, "signals": signals, "facts": facts}


def compute_gap(state: dict, item: dict, index: int) -> dict | None:
    q, ans = item["q_seq"], item.get("answer_seq")
    last = state["messages"][-1]["seq"]
    end = ans - 1 if ans else last
    others = [m["seq"] for m in state["messages"] if m["seq"] > q and m["sender"] != item["raiser"]]

    stages, prev = [], None
    for k in range(q + 1, end + 1):
        st = _state_at(state, item, k, others)
        if not st:
            continue
        signature = (st["type"], tuple(sorted(st["signals"].items())))
        if signature != prev:
            sc = score(st["signals"])
            stages.append({"at": k, **st, "score": sc, "severity": severity(sc)})
            prev = signature
    if not stages:
        return None

    latest = _state_at(state, item, end, others) if end > q else None
    if latest:
        stages[-1]["facts"] = latest["facts"]  # the newest stage explains the conversation so far
    topic = item.get("topic_name") or _topic_from_question(state, q)
    return {
        "id": item["id"],
        "item": index,
        "q_seq": q,
        "topic": topic,
        "topicKey": item.get("topic_key"),
        "raisedBy": item["raiser"],
        "resolvedAt": ans if ans else None,
        "resolvedBy": item.get("answer_by") if ans else None,
        "stages": stages,
        "critic": {},
    }


def _topic_from_question(state: dict, seq: int) -> str:
    words = AgentContext.meaning(state, seq).rstrip("?.! ").split()
    return " ".join(words[:5]) + ("…" if len(words) > 5 else "")


def gap_detector(ctx: AgentContext, state: dict) -> dict:
    ctx.stage(AGENT)
    gaps = []
    for i, item in enumerate(state.get("items") or []):
        gap = compute_gap(state, item, i)
        if gap:
            gaps.append(gap)
    open_gaps = [i for i, g in enumerate(gaps) if g["resolvedAt"] is None]
    if gaps:
        detail = ", ".join(f"{g['topic']} ({g['stages'][-1]['score']:.2f})" for g in gaps)
        ctx.log(AGENT, f"Scored {len(state.get('items') or [])} thread(s): {len(gaps)} became gaps – {detail}. "
                       f"Sending {len(open_gaps)} open gap(s) to the Critic.")
    else:
        ctx.log(AGENT, f"Scored {len(state.get('items') or [])} thread(s). No communication gaps.")
    return {"gaps": gaps, "critic_queue": open_gaps}
