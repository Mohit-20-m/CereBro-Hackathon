"""Agent 4 – Response Matcher (agentic).

Walks through every message that expects a reply, one per graph step:
  * if it repeats or clarifies an open question, it is attached to that thread;
  * otherwise it opens a new thread and checks the next few replies from other
    people. Embedding similarity picks which replies are worth judging; the
    mDeBERTa NLI model judges each one (answers / postpones / unrelated).
  * if nothing in that window answers it and the conversation continues, the
    matcher hands the thread to the Investigator agent, which searches the rest
    of the chat with tools before returning control here.
"""
from __future__ import annotations

from ..ai.lexicon import (
    is_bare_reply,
    is_open_question,
    looks_like_clarification,
    looks_like_deflection,
    looks_like_repeat,
    starts_with_yes_no,
    tokens,
)
from ..config import settings
from ..ml.embeddings import thresholds
from ..ml.engine import engine
from .context import AgentContext

AGENT = "Response Matcher"
VERDICTS = {"ANSWERED", "DEFLECTION", "NOT_ANSWER"}
SOON_MIN_SIM = 0.2  # loose link needed when the same person re-asks within 3 messages
JUDGE_LABELS = {
    "answers the question": "ANSWERED",
    "postpones or avoids giving an answer": "DEFLECTION",
    "talks about something else": "NOT_ANSWER",
}
VERDICT_TEXT = {
    "ANSWERED": "Answers the question",
    "DEFLECTION": "Postpones without answering",
    "NOT_ANSWER": "Does not answer it",
}


def msg_by_seq(state: dict, seq: int) -> dict:
    return next(m for m in state["messages"] if m["seq"] == seq)


def is_open_at(item: dict, seq: int) -> bool:
    return item.get("answer_seq") is None or item["answer_seq"] > seq


def _replies_right_after(state: dict, item: dict, cand_seq: int) -> bool:
    """True when the reply directly follows the question or one of its re-asks."""
    prev = next((m for m in state["messages"] if m["seq"] == cand_seq - 1), None)
    return bool(prev) and prev["sender"] == item["raiser"] and state["analyses"].get(prev["seq"], {}).get("requires_response")


# ---------------------------------------------------------------------------
# Judge: does reply `cand_seq` answer the thread's question?
# ---------------------------------------------------------------------------
def judge(ctx: AgentContext, state: dict, item: dict, cand_seq: int) -> dict:
    q = msg_by_seq(state, item["q_seq"])
    c = msg_by_seq(state, cand_seq)
    key = f"{q['db_id']}:{c['db_id']}"
    cached = ctx.cache_get("judge", key)
    if cached:
        return cached

    q_meaning = AgentContext.meaning(state, q["seq"])
    c_meaning = AgentContext.meaning(state, c["seq"])
    sim = AgentContext.similarity(state, q["seq"], c["seq"])
    ca = state["analyses"].get(cand_seq, {})
    same_topic = bool(item.get("topic_key")) and ca.get("topic_key") == item["topic_key"]
    adjacent = _replies_right_after(state, item, cand_seq)

    if engine.nli_ok:
        premise = f'{q["sender"]} asked: "{q_meaning}"\n{c["sender"]} replied: "{c_meaning}"'
        scores = engine.classify(premise, list(JUDGE_LABELS), "The reply {}.")
        label, p = max(scores.items(), key=lambda kv: kv[1])
        verdict = JUDGE_LABELS[label]
        result = {"verdict": verdict, "reason": f"{VERDICT_TEXT[verdict]} (NLI {p:.2f}).", "source": "nli",
                  "p": round(p, 2)}
        # An "answer" must be connected to the question somehow.
        if verdict == "ANSWERED" and not (adjacent or same_topic or sim >= thresholds(ca.get("embed_model"))["candidate"]):
            result = {"verdict": "NOT_ANSWER", "source": "nli+context",
                      "reason": f"Not connected to the question (NLI said answer {p:.2f}, similarity {sim:.2f})."}
    else:
        result = _fallback_judge(state, item, cand_seq, q_meaning, c_meaning, sim, same_topic, adjacent)
        ctx.fallbacks += 1

    # Guard rails: a bare yes/ok never answers a who/which/either-or question,
    # and a short "I'll check" is a deflection.
    if result["verdict"] == "ANSWERED" and is_bare_reply(c["text"]) and is_open_question(q_meaning):
        result = {"verdict": "NOT_ANSWER", "reason": "A bare yes/no does not answer an open question.", "source": "rule"}
    elif result["verdict"] == "ANSWERED" and looks_like_deflection(c_meaning) and len(tokens(c_meaning)) <= 5:
        result = {"verdict": "DEFLECTION", "reason": "Postpones without giving an answer.", "source": "rule"}
    ctx.cache_set("judge", key, result)
    return result


def _fallback_judge(state, item, cand_seq, q_meaning, c_meaning, sim, same_topic, adjacent) -> dict:
    c = state["analyses"].get(cand_seq, {})
    if looks_like_deflection(c_meaning):
        return {"verdict": "DEFLECTION", "reason": "Postpones without giving an answer.", "source": "fallback"}
    if adjacent and not is_open_question(q_meaning) and starts_with_yes_no(c_meaning):
        return {"verdict": "ANSWERED", "reason": "Answers the yes/no question directly.", "source": "fallback"}
    if adjacent and c.get("intent") in {"PROMISE", "ANSWER"} and is_open_question(q_meaning) and not is_bare_reply(c_meaning):
        return {"verdict": "ANSWERED", "reason": "Takes ownership right after the question.", "source": "fallback"}
    if same_topic and c.get("intent") in {"ANSWER", "STATEMENT", "PROMISE", "CONFIRMATION"}:
        return {"verdict": "ANSWERED", "reason": "Replies on the same topic.", "source": "fallback"}
    if sim >= thresholds(c.get("embed_model"))["merge"]:
        return {"verdict": "ANSWERED", "reason": "Very close in meaning to the question.", "source": "fallback"}
    return {"verdict": "NOT_ANSWER", "reason": "About a different subject.", "source": "fallback"}


def record_check(item: dict, seq: int, verdict: dict, sim: float, judged: bool, by: str) -> None:
    item["checked"] = [c for c in item["checked"] if c["seq"] != seq]
    item["checked"].append({"seq": seq, "verdict": verdict["verdict"], "reason": verdict.get("reason", ""),
                            "sim": round(sim, 2), "judged": judged, "by": by})
    item["checked"].sort(key=lambda c: c["seq"])
    if verdict["verdict"] == "DEFLECTION" and seq not in item["deflections"]:
        item["deflections"].append(seq)
        item["deflections"].sort()


# ---------------------------------------------------------------------------
# Graph node
# ---------------------------------------------------------------------------
def response_matcher(ctx: AgentContext, state: dict) -> dict:
    ctx.stage(AGENT)
    analyses = state["analyses"]
    items = state.get("items") or []
    pending = state.get("pending")
    if pending is None:  # first visit: queue every message that expects a reply
        pending = [m["seq"] for m in state["messages"] if analyses[m["seq"]].get("requires_response")]
        ctx.log(AGENT, f"{len(pending)} message(s) expect a reply. Checking each one.")
    pending = list(pending)
    if not pending:
        return {"items": items, "pending": [], "current": None}

    seq = pending.pop(0)
    m = msg_by_seq(state, seq)
    a = analyses[seq]
    text = f"{m['text']} {a.get('normalized') or ''}"
    th = thresholds(a.get("embed_model"))

    # 1) Is this a repeat / clarification of a thread that is still open?
    for item in reversed(items):
        if not is_open_at(item, seq):
            continue
        sim = AgentContext.similarity(state, seq, item["q_seq"])
        same_topic = bool(a.get("topic_key")) and a.get("topic_key") == item.get("topic_key")
        re_ask = looks_like_repeat(text) or looks_like_clarification(text)
        same_person = m["sender"] == item["raiser"]
        latest_own = item is _latest_open_by(items, m["sender"], seq)
        # Same person asking again soon after getting no answer, on a related subject.
        soon = (same_person and latest_own and seq - _last_seq(item) <= 3 and sim >= SOON_MIN_SIM
                and a.get("intent") in {"QUESTION", "CLARIFICATION", "REQUEST"})
        if (same_topic and (same_person or a.get("intent") in {"REQUEST", "CLARIFICATION"})) or sim >= th["merge"] \
                or (re_ask and same_person and latest_own) or soon:
            rephrased = a.get("intent") == "CLARIFICATION" or looks_like_clarification(text) or (soon and sim < th["merge"] and not same_topic)
            role = "followup" if rephrased else "repeat"
            item["followups"].append({"seq": seq, "role": role, "sender": m["sender"]})
            why = ("same topic" if same_topic else f"similarity {sim:.2f}" if sim >= th["merge"]
                   else "re-ask wording" if re_ask else f"re-asked soon after, similarity {sim:.2f}")
            ctx.log(AGENT, f"#{seq} {'clarifies' if role == 'followup' else 'repeats'} the question in #{item['q_seq']} ({why}).")
            return {"items": items, "pending": pending, "current": None}

    # 2) New thread: check the next replies from other people.
    item = {
        "id": f"gap-{m['db_id']}",
        "q_seq": seq,
        "raiser": m["sender"],
        "intent": a.get("intent"),
        "topic_key": a.get("topic_key"),
        "topic_name": a.get("topic_name"),
        "followups": [],
        "checked": [],
        "deflections": [],
        "answer_seq": None,
        "answer_by": None,
        "answer_reason": None,
        "investigation": None,
    }
    items.append(item)
    others = [x for x in state["messages"] if x["seq"] > seq and x["sender"] != m["sender"]]
    window = others[: settings.response_window]

    for i, c in enumerate(window):
        ca = analyses[c["seq"]]
        sim = AgentContext.similarity(state, seq, c["seq"])
        worth = (
            i == 0
            or (item["topic_key"] and ca.get("topic_key") == item["topic_key"])
            or sim >= th["candidate"]
            or ca.get("intent") in {"ANSWER", "PROMISE"}
        )
        if worth:
            verdict = judge(ctx, state, item, c["seq"])
        else:
            verdict = {"verdict": "NOT_ANSWER", "reason": f"About {ca.get('topic_name') or 'something else'}."}
        record_check(item, c["seq"], verdict, sim, worth, AGENT)
        if verdict["verdict"] == "ANSWERED":
            item.update(answer_seq=c["seq"], answer_by=AGENT, answer_reason=verdict.get("reason"))
            break

    if item["answer_seq"]:
        ctx.log(AGENT, f"#{seq} ({item['topic_name'] or 'question'}) is answered by #{item['answer_seq']}.")
        return {"items": items, "pending": pending, "current": None}
    if len(others) > len(window):
        ctx.log(AGENT, f"#{seq} has no answer in the next {len(window)} replies. Not sure yet, so asking the Investigator.")
        return {"items": items, "pending": pending, "current": {"item": len(items) - 1, "steps": []}}
    ctx.log(AGENT, f"#{seq} has no answer so far ({len(window)} repl{'y' if len(window) == 1 else 'ies'} checked).")
    return {"items": items, "pending": pending, "current": None}


def _last_seq(item: dict) -> int:
    return max([item["q_seq"]] + [f["seq"] for f in item["followups"]])


def _latest_open_by(items: list[dict], sender: str, seq: int) -> dict | None:
    for item in reversed(items):
        if item["raiser"] == sender and is_open_at(item, seq):
            return item
    return None
