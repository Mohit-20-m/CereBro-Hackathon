"""Investigator agent (part of the agentic Response Matcher).

Runs a small tool loop, one tool call per graph step; LangGraph loops this node
until it decides to stop. Each step it looks at what it has found so far and
chooses the next tool (meaning search, topic search, speaker lookup) or stops.
The choice is made by a confidence-based policy over the tool results, or by
the optional LLM (ReAct style) when one is connected. Any message it proposes
is verified by the NLI judge before it counts.
"""
from __future__ import annotations

from ..ml.embeddings import thresholds
from ..ai.prompts import INVESTIGATOR_SCHEMA, INVESTIGATOR_SYSTEM, INVESTIGATOR_TOOLS
from ..config import settings
from .context import AgentContext
from .matcher import judge, msg_by_seq, record_check
from .tools import TOOLS, format_observation

AGENT = "Investigator"


def investigator(ctx: AgentContext, state: dict) -> dict:
    ctx.stage(AGENT)
    cur = dict(state["current"])
    items = state["items"]
    item = items[cur["item"]]
    q = msg_by_seq(state, item["q_seq"])
    last_seq = state["messages"][-1]["seq"]
    cache_key = str(q["db_id"])

    if not cur["steps"]:
        cached = ctx.cache_get("investigation", cache_key)
        if cached and cached.get("last_seq") == last_seq:
            _apply(item, cached)
            found = f"answer at #{cached['answer_seq']}" if cached.get("answer_seq") else "no answer"
            ctx.log(AGENT, f"#{item['q_seq']}: nothing new since the last search ({found}).")
            return {"items": items, "current": None}
        if cached and cached.get("last_seq", 0) < last_seq and not cached.get("answer_seq"):
            _apply(item, cached)
            return _recheck_new(ctx, state, item, cache_key, cached["last_seq"])

    if len(cur["steps"]) < settings.investigator_max_steps:
        decision = None
        if ctx.llm.available:
            decision = ctx.llm.chat_json(
                INVESTIGATOR_SYSTEM.format(steps=settings.investigator_max_steps),
                _prompt(state, item, cur["steps"]),
                INVESTIGATOR_SCHEMA,
                num_predict=120,
            )
        if not decision or decision.get("action") not in INVESTIGATOR_TOOLS:
            decision = _policy(state, item, cur["steps"])
        action = decision["action"]
        if action in TOOLS:
            arg = str(decision.get("input") or "")
            rows = TOOLS[action](ctx, state, item, arg)
            cur["steps"].append({"thought": str(decision.get("thought") or "")[:200], "action": action,
                                 "input": arg[:120], "rows": rows})
            found = ", ".join(f"#{r['seq']}" for r in rows) or "nothing"
            ctx.log(AGENT, f"#{item['q_seq']}: {decision.get('thought') or action} → {action}(\"{arg[:60]}\") → {found}")
            return {"items": items, "current": cur}
        proposal = decision.get("answer_seq") or 0
        if decision.get("thought"):
            ctx.log(AGENT, f"#{item['q_seq']}: {decision['thought']}")
        return _finish(ctx, state, item, cur, cache_key, proposal if isinstance(proposal, int) else 0)
    return _finish(ctx, state, item, cur, cache_key, 0)


def _policy(state: dict, item: dict, steps: list[dict]) -> dict:
    """Chooses the next tool from what earlier tools returned (no LLM needed)."""
    q_seq = item["q_seq"]
    checked = {c["seq"] for c in item["checked"]}
    strong = thresholds(state["analyses"][q_seq].get("embed_model"))["strong"]
    rows = [r for s in steps for r in s["rows"] if r["seq"] not in checked and r["sender"] != item["raiser"]]
    best = max((r.get("sim", 0) for r in rows), default=0)
    used = {s["action"] for s in steps}

    if not steps:
        return {"action": "find_similar", "input": AgentContext.meaning(state, q_seq),
                "thought": "Looking for later messages with a similar meaning"}
    if best >= strong:
        return {"action": "final", "answer_seq": 0, "thought": f"Found a strong match ({best:.2f}); verifying it"}
    if item.get("topic_name") and "search_messages" not in used:
        return {"action": "search_messages", "input": item["topic_name"],
                "thought": f"No strong match; searching for the topic \"{item['topic_name']}\""}
    question = msg_by_seq(state, q_seq)["text"].lower()
    mentioned = [m["sender"] for m in state["messages"]
                 if m["sender"] != item["raiser"] and m["sender"].lower() in question]
    if mentioned and "get_messages_by_speaker" not in used:
        return {"action": "get_messages_by_speaker", "input": mentioned[0],
                "thought": f"The question mentions {mentioned[0]}; reading their replies"}
    return {"action": "final", "answer_seq": 0, "thought": "Searched enough; verifying the best candidates"}


def _prompt(state: dict, item: dict, steps: list[dict]) -> str:
    q_seq = item["q_seq"]
    members = sorted({m["sender"] for m in state["messages"]})
    checked = ", ".join(f"#{c['seq']}" for c in item["checked"]) or "none"
    lines = [
        f"Question #{q_seq} by {item['raiser']}: {msg_by_seq(state, q_seq)['text']}",
        f"Meaning: {AgentContext.meaning(state, q_seq)}",
        f"Participants: {', '.join(members)}",
        f"Later messages exist from #{q_seq + 1} to #{state['messages'][-1]['seq']}.",
        f"Already checked, not answers: {checked}",
    ]
    if steps:
        lines.append("Your previous tool calls:")
        for i, s in enumerate(steps, 1):
            lines.append(f"{i}. {s['action']}(\"{s['input']}\")\n{format_observation(s['rows'])}")
    left = settings.investigator_max_steps - len(steps)
    lines.append(f"Tool calls left: {left}. {'Call final now.' if left <= 0 else 'What is your next action?'}")
    return "\n".join(lines)


def _finish(ctx: AgentContext, state: dict, item: dict, cur: dict, cache_key: str, proposal: int) -> dict:
    """Verify the proposal, then fall back to the best candidates the tools surfaced."""
    q_seq, raiser = item["q_seq"], item["raiser"]
    checked = {c["seq"] for c in item["checked"]}
    valid = {m["seq"] for m in state["messages"] if m["seq"] > q_seq and m["sender"] != raiser}

    candidates: list[int] = []
    if proposal in valid:
        candidates.append(proposal)
    seen_rows = [r for s in cur["steps"] for r in s["rows"]]
    if not seen_rows:  # no tool use (heuristic mode or model failure): use similarity directly
        th = thresholds(state["analyses"][q_seq].get("embed_model"))
        seen_rows = [
            {"seq": s, "sim": AgentContext.similarity(state, q_seq, s)} for s in sorted(valid - checked)
        ]
        seen_rows = [r for r in seen_rows if r["sim"] >= th["candidate"]
                     or state["analyses"][r["seq"]].get("topic_key") == item["topic_key"] and item["topic_key"]]
    for r in sorted(seen_rows, key=lambda r: -r.get("sim", 0)):
        if r["seq"] in valid and r["seq"] not in checked and r["seq"] not in candidates:
            candidates.append(r["seq"])
    candidates = candidates[:3]

    answer = None
    for seq in candidates:
        verdict = judge(ctx, state, item, seq)
        record_check(item, seq, verdict, AgentContext.similarity(state, q_seq, seq), True, AGENT)
        if verdict["verdict"] == "ANSWERED":
            answer = seq
            item.update(answer_seq=seq, answer_by=AGENT, answer_reason=verdict.get("reason"))
            break

    steps = [{"action": s["action"], "input": s["input"], "found": [r["seq"] for r in s["rows"]]} for s in cur["steps"]]
    item["investigation"] = {"steps": steps, "found": answer, "verified": candidates}
    _save(ctx, state, item, cache_key)
    if answer:
        ctx.log(AGENT, f"#{q_seq}: found the answer later in the chat at #{answer} (verified by the judge).")
    else:
        tried = f"verified {', '.join('#' + str(s) for s in candidates)}" if candidates else "no candidates"
        ctx.log(AGENT, f"#{q_seq}: searched the rest of the chat ({len(steps)} tool call(s), {tried}). No answer.")
    return {"items": state["items"], "current": None}


def _save(ctx: AgentContext, state: dict, item: dict, cache_key: str) -> None:
    ctx.cache_set("investigation", cache_key, {
        "last_seq": state["messages"][-1]["seq"], "answer_seq": item.get("answer_seq"),
        "answer_reason": item.get("answer_reason"), "checked": item["checked"],
        "deflections": item["deflections"], "investigation": item["investigation"],
    })


def _recheck_new(ctx: AgentContext, state: dict, item: dict, cache_key: str, since: int) -> dict:
    """An earlier search found nothing: only messages that arrived since then need checking."""
    q_seq = item["q_seq"]
    th = thresholds(state["analyses"][q_seq].get("embed_model"))
    fresh = [m for m in state["messages"] if m["seq"] > since and m["sender"] != item["raiser"]]
    worth = []
    for m in fresh:
        a = state["analyses"][m["seq"]]
        sim = AgentContext.similarity(state, q_seq, m["seq"])
        if sim >= th["candidate"] or (item["topic_key"] and a.get("topic_key") == item["topic_key"]) \
                or a.get("intent") in {"ANSWER", "PROMISE"}:
            worth.append((sim, m["seq"]))
    for sim, seq in sorted(worth, reverse=True)[:3]:
        verdict = judge(ctx, state, item, seq)
        record_check(item, seq, verdict, sim, True, AGENT)
        if verdict["verdict"] == "ANSWERED":
            item.update(answer_seq=seq, answer_by=AGENT, answer_reason=verdict.get("reason"))
            break
    inv = dict(item.get("investigation") or {"steps": []})
    inv["found"] = item.get("answer_seq")
    item["investigation"] = inv
    _save(ctx, state, item, cache_key)
    if item.get("answer_seq"):
        ctx.log(AGENT, f"#{q_seq}: a new message (#{item['answer_seq']}) answers it (verified by the judge).")
    else:
        ctx.log(AGENT, f"#{q_seq}: re-checked {len(fresh)} new message(s) ({len(worth)} relevant). Still no answer.")
    return {"items": state["items"], "current": None}


def _apply(item: dict, cached: dict) -> None:
    item["checked"] = cached.get("checked", item["checked"])
    item["deflections"] = cached.get("deflections", item["deflections"])
    item["investigation"] = cached.get("investigation")
    if cached.get("answer_seq"):
        item.update(answer_seq=cached["answer_seq"], answer_by=AGENT, answer_reason=cached.get("answer_reason"))


__all__ = ["investigator", "INVESTIGATOR_TOOLS"]
