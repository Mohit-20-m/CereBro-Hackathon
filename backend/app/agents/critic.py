"""Agent 6 – Critic (agentic).

Challenges every open gap before it reaches the user: "is there any message
that resolves this?" It independently re-checks the later replies the matcher
did not judge (ranked by meaning) with the NLI model, or asks the optional LLM
to re-read the conversation. A gap is only marked resolved if the NLI judge
agrees. LangGraph loops this node until every open gap has been reviewed.
"""
from __future__ import annotations

from ..ai.prompts import CRITIC_SCHEMA, CRITIC_SYSTEM
from ..config import settings
from ..ml.embeddings import thresholds
from ..ml.engine import engine
from .context import AgentContext
from .gap_detector import GAP_LABELS, compute_gap
from .matcher import judge, msg_by_seq

AGENT = "Critic"


def critic(ctx: AgentContext, state: dict) -> dict:
    ctx.stage(AGENT)
    queue = list(state.get("critic_queue") or [])
    gaps = list(state["gaps"])
    if not queue:
        return {"critic_queue": []}
    idx = queue.pop(0)
    gap = gaps[idx]
    item = state["items"][gap["item"]]
    q = msg_by_seq(state, item["q_seq"])
    last_seq = state["messages"][-1]["seq"]
    cache_key = str(q["db_id"])
    review = ctx.cache_get("critic", cache_key)
    if not review or review.get("verdict") == "resolved" or review.get("last_seq", 0) < last_seq:
        since = review.get("last_seq", 0) if review and review.get("verdict") == "confirmed" else item["q_seq"]
        later = [m for m in state["messages"] if m["seq"] > max(since, item["q_seq"])][-settings.critic_context_messages:]
        fresh = _review(ctx, state, item, gap, later)
        if fresh["verdict"] == "confirmed" and review and review.get("verdict") == "confirmed":
            fresh["checked"] = review.get("checked", 0) + fresh["checked"]
        review = {**fresh, "last_seq": last_seq}
        ctx.cache_set("critic", cache_key, review)

    if review["verdict"] == "resolved":
        item.update(answer_seq=review["seq"], answer_by=AGENT, answer_reason=review.get("reason"))
        updated = compute_gap(state, item, gap["item"])
        if updated is None:
            gaps[idx] = None  # resolved before it ever became a gap
            ctx.log(AGENT, f"Rejected the gap on {gap['topic']}: #{review['seq']} answers it straight away.")
        else:
            updated["critic"] = review
            gaps[idx] = updated
            ctx.log(AGENT, f"Challenged the gap on {gap['topic']}: #{review['seq']} resolves it (judge agreed).")
    else:
        gap["critic"] = review
        if review["verdict"] == "confirmed":
            extra = f" Rejected its own suggestion #{review['rejected']}." if review.get("rejected") else ""
            ctx.log(AGENT, f"Confirmed the gap on {gap['topic']} after re-reading {review['checked']} message(s).{extra}")
        else:
            ctx.log(AGENT, f"Could not review the gap on {gap['topic']}; kept the detector's decision.")
    return {"gaps": gaps, "critic_queue": queue, "items": state["items"]}


def _review(ctx: AgentContext, state: dict, item: dict, gap: dict, later: list[dict]) -> dict:
    claim = (
        f"Claim: {GAP_LABELS[gap['stages'][-1]['type']].lower()} – the question in #{item['q_seq']} by "
        f"{item['raiser']} about {gap['topic']} was never answered."
    )
    prompt = (
        f"{claim}\n\nQuestion: {AgentContext.describe(state, item['q_seq'])}\n\nLater messages:\n"
        + "\n".join(AgentContext.describe(state, m["seq"]) for m in later)
    )
    out = ctx.llm.chat_json(CRITIC_SYSTEM, prompt, CRITIC_SCHEMA, num_predict=80) if ctx.llm.available else None
    if not out:
        return _review_with_models(ctx, state, item, later)

    reason = (out.get("reason") or "").strip()
    seq = out.get("message_seq") if isinstance(out.get("message_seq"), int) else 0
    valid = {m["seq"] for m in later if m["sender"] != item["raiser"]}
    if out.get("resolved") and seq in valid:
        verdict = judge(ctx, state, item, seq)
        if verdict["verdict"] == "ANSWERED":
            return {"verdict": "resolved", "seq": seq, "checked": len(later), "reason": reason or verdict["reason"], "source": "llm"}
        return {"verdict": "confirmed", "rejected": seq, "checked": len(later), "source": "llm",
                "reason": f"Suggested #{seq}, but the judge disagreed: {verdict['reason']}"}
    return {"verdict": "confirmed", "checked": len(later), "reason": reason, "source": "llm"}


def _review_with_models(ctx: AgentContext, state: dict, item: dict, later: list[dict]) -> dict:
    """Independent check: judge the most related replies the matcher never looked at."""
    if not engine.embed_ok:
        return {"verdict": "unverified", "checked": len(later), "reason": "", "source": "fallback"}
    judged = {c["seq"] for c in item["checked"]}
    th = thresholds(state["analyses"][item["q_seq"]].get("embed_model"))
    pool = []
    for m in later:
        if m["sender"] == item["raiser"] or m["seq"] in judged:
            continue
        sim = AgentContext.similarity(state, item["q_seq"], m["seq"])
        same_topic = item.get("topic_key") and state["analyses"][m["seq"]].get("topic_key") == item["topic_key"]
        if sim >= th["candidate"] * 0.8 or same_topic:
            pool.append((sim, m["seq"]))
    for sim, seq in sorted(pool, reverse=True)[:4]:
        verdict = judge(ctx, state, item, seq)
        if verdict["verdict"] == "ANSWERED":
            return {"verdict": "resolved", "seq": seq, "checked": len(later), "source": "nli",
                    "reason": f"#{seq} answers it: {verdict['reason']}"}
    return {"verdict": "confirmed", "checked": len(later), "source": "nli",
            "reason": f"Re-checked {len(pool)} related repl{'y' if len(pool) == 1 else 'ies'} with the NLI model; none answers it."}
