"""Agent 7 – Evidence Generator.

Turns each confirmed gap into something a person can check: the exact
messages involved (each with its role and a note), plain-language reasons for
every stage, an explainable confidence value and a one-sentence summary.
It also tracks the status of every topic over time and computes insights.
"""
from __future__ import annotations

from ..ai.prompts import SUMMARY_SCHEMA, SUMMARY_SYSTEM
from .context import AgentContext
from .gap_detector import GAP_LABELS
from ..ml.engine import engine
from .matcher import msg_by_seq

AGENT = "Evidence Generator"


def _quote(text: str, limit: int = 40) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _evidence(state: dict, gap: dict, item: dict) -> list[dict]:
    end = gap["resolvedAt"] or 10**9
    q_intent = (item.get("intent") or "QUESTION").lower()
    rows: dict[int, dict] = {
        item["q_seq"]: {"id": item["q_seq"], "role": "question",
                        "note": f"Detected as a {q_intent} that needs a reply."}
    }
    for c in item["checked"]:
        if c["seq"] >= end or c["verdict"] == "ANSWERED":
            continue
        role = "deflection" if c["verdict"] == "DEFLECTION" else "unrelated"
        note = c.get("reason") or ""
        note = f"{note} Similarity {c['sim']:.2f}".strip()
        if c.get("by") == "Investigator":
            note += " · checked by the Investigator"
        rows[c["seq"]] = {"id": c["seq"], "role": role, "note": note}
    for f in item["followups"]:
        if f["seq"] >= end:
            continue
        who = f["sender"]
        if f["role"] == "followup":
            note = f"{who} rephrases the question."
        elif who == item["raiser"]:
            note = f"{who} asks again."
        else:
            note = f"{who} raises the same question."
        rows[f["seq"]] = {"id": f["seq"], "role": f["role"], "note": note}
    if gap["resolvedAt"]:
        by = gap.get("resolvedBy") or "Response Matcher"
        reason = (item.get("answer_reason") or "Answers the question.").rstrip(".")
        rows[gap["resolvedAt"]] = {"id": gap["resolvedAt"], "role": "resolution", "note": f"{reason}. Found by the {by}."}
    return [rows[k] for k in sorted(rows)]


def _reasons(state: dict, gap: dict, item: dict, stage: dict, final: bool) -> list[str]:
    facts = stage["facts"]
    raiser, topic = item["raiser"], gap["topic"]
    kind = "request" if item.get("intent") == "REQUEST" else "question"
    out = [f"{raiser} raised a {kind} about {topic}."]
    n = facts["replies"]
    if n:
        out.append(f"{n} repl{'y' if n == 1 else 'ies'} since then did not answer it.")
    for d in facts["deflections"]:
        m = msg_by_seq(state, d)
        out.append(f"{m['sender']} only replied \"{_quote(m['text'])}\", with no clear answer.")
    repeats = [f for f in facts["followups"] if f["role"] == "repeat"]
    own = [f for f in repeats if f["sender"] == raiser]
    if own:
        out.append(f"{raiser} had to ask again." if len(own) == 1 else f"{raiser} asked again {len(own)} times.")
    for f in repeats:
        if f["sender"] != raiser:
            out.append(f"{f['sender']} raised the same question.")
    if stage["signals"]["clarification"]:
        out.append("The question was rephrased to clarify it, and still got no answer.")
    if stage["signals"]["recurrence"]:
        out.append("The topic came up again without a decision.")
    if final:
        inv = item.get("investigation")
        if inv and not inv.get("found"):
            calls = len(inv.get("steps") or [])
            if calls:
                out.append(f"The Investigator searched the rest of the chat ({calls} tool call{'s' if calls != 1 else ''}) and found no answer.")
            else:
                out.append("The Investigator compared the rest of the chat by meaning and found no answer.")
        critic = gap.get("critic") or {}
        if critic.get("verdict") == "confirmed":
            out.append(f"The Critic re-read {critic.get('checked', 0)} later messages and found nothing that resolves it.")
    return out


def _confidence(stage: dict, gap: dict, final: bool, heuristic: bool) -> int:
    """Explainable: 45 + 45 × score + 2 per unanswered reply (max 5),
    +4 when the Critic confirmed the gap, −10 in heuristic mode."""
    value = 45 + 45 * stage["score"] + 2 * min(stage["facts"]["replies"], 5)
    if final and (gap.get("critic") or {}).get("verdict") == "confirmed":
        value += 4
    if heuristic:
        value -= 10
    return int(max(30, min(97, round(value))))


def _summary(ctx: AgentContext, state: dict, gap: dict, item: dict, reasons: list[str], evidence: list[dict]) -> str:
    q = msg_by_seq(state, item["q_seq"])
    facts = gap["stages"][-1]["facts"]
    key = (f"{q['db_id']}:{gap['stages'][-1]['type']}:{gap['resolvedAt']}:{len(facts['followups'])}:"
           f"{len(facts['deflections'])}:{min(facts['replies'], 5)}")
    cached = ctx.cache_get("summary", key)
    if cached and cached.get("text"):
        return cached["text"]
    status = f"resolved at message #{gap['resolvedAt']}" if gap["resolvedAt"] else "still unresolved"
    prompt = (
        f"Gap type: {GAP_LABELS[gap['stages'][-1]['type']]}\nTopic: {gap['topic']}\nRaised by: {item['raiser']}\n"
        f"Question: {AgentContext.meaning(state, item['q_seq'])}\nStatus: {status}\nFacts:\n- " + "\n- ".join(reasons)
    )
    out = ctx.llm.chat_json(SUMMARY_SYSTEM, prompt, SUMMARY_SCHEMA, num_predict=70) if ctx.llm.available else None
    text = (out or {}).get("summary", "").strip() if out else ""
    if not text:
        text = _template_summary(state, gap, item)
    ctx.cache_set("summary", key, {"text": text})
    return text


def _template_summary(state: dict, gap: dict, item: dict) -> str:
    facts = gap["stages"][-1]["facts"]
    kind = "request" if item.get("intent") == "REQUEST" else "question"
    repeats = len([f for f in facts["followups"] if f["role"] == "repeat"])
    clar = len([f for f in facts["followups"] if f["role"] == "followup"])
    events = []
    if repeats:
        events.append("was asked again" if repeats == 1 else f"was asked again {repeats} times")
    if clar:
        events.append("had to be rephrased")
    if facts["deflections"]:
        events.append("only got a postponement")
    if gap["resolvedAt"]:
        end = f"was finally answered in message #{gap['resolvedAt']}"
    else:
        n = facts["replies"]
        end = f"is still unanswered after {n} repl{'y' if n == 1 else 'ies'}"
    middle = (", ".join(events) + ", and ") if events else ""
    return f"{item['raiser']}'s {kind} about {gap['topic']} {middle}{end}."


def track_topics(state: dict, gaps: list[dict]) -> list[dict]:
    """Status of every topic after each message: pending, unresolved or resolved."""
    analyses, items = state["analyses"], state.get("items") or []
    seen: dict[str, dict] = {}
    promise: dict[str, bool] = {}
    for m in state["messages"]:
        k = m["seq"]
        a = analyses.get(k, {})
        t = a.get("topic_key")
        if t:
            info = seen.setdefault(t, {"key": t, "name": a.get("topic_name") or t, "first": k, "timeline": []})
            info["last"] = k
            answers_item = any(i.get("answer_seq") == k for i in items)
            if a.get("intent") == "PROMISE" and not answers_item:
                promise[t] = True
            elif a.get("intent") in {"ANSWER", "STATEMENT", "CONFIRMATION"} or answers_item:
                promise[t] = False
        for key, info in seen.items():
            if any(g["topicKey"] == key and g["stages"][0]["at"] <= k and (g["resolvedAt"] is None or g["resolvedAt"] > k)
                   for g in gaps):
                status = "unresolved"
            elif any(i.get("topic_key") == key and i["q_seq"] <= k and (i.get("answer_seq") is None or i["answer_seq"] > k)
                     for i in items) or promise.get(key):
                status = "pending"
            else:
                status = "resolved"
            if not info["timeline"] or info["timeline"][-1]["status"] != status:
                info["timeline"].append({"at": k, "status": status})
    out = []
    for info in seen.values():
        info.setdefault("last", info["first"])
        info["status"] = info["timeline"][-1]["status"]
        out.append(info)
    return out


def compute_insights(state: dict, gaps: list[dict], topics: list[dict]) -> dict:
    intents = [state["analyses"].get(m["seq"], {}).get("intent") for m in state["messages"]]
    questions = intents.count("QUESTION")
    unanswered = sum(1 for g in gaps if not g["resolvedAt"])
    return {
        "messages": len(state["messages"]),
        "questions": questions,
        "unanswered": unanswered,
        "answered": max(0, questions - unanswered),
        "requests": intents.count("REQUEST") + intents.count("CLARIFICATION"),
        "loops": sum(1 for g in gaps if g["type"] == "CLARIFICATION_LOOP"),
        "unresolvedTopics": sum(1 for t in topics if t["status"] == "unresolved"),
        "resolvedTopics": sum(1 for t in topics if t["status"] == "resolved"),
        "pendingTopics": sum(1 for t in topics if t["status"] == "pending"),
        "codeMixed": sum(1 for m in state["messages"] if state["analyses"].get(m["seq"], {}).get("is_code_mixed")),
    }


def evidence_generator(ctx: AgentContext, state: dict) -> dict:
    ctx.stage(AGENT)
    heuristic = not engine.embed_ok
    gaps = [g for g in state.get("gaps") or [] if g]
    for gap in gaps:
        item = state["items"][gap["item"]]
        evidence = _evidence(state, gap, item)
        for i, stage in enumerate(gap["stages"]):
            final = i == len(gap["stages"]) - 1
            stage["reasons"] = _reasons(state, gap, item, stage, final)
            stage["confidence"] = _confidence(stage, gap, final, heuristic)
        last = gap["stages"][-1]
        gap.update(
            evidence=evidence,
            type=last["type"],
            signals=last["signals"],
            score=last["score"],
            severity=last["severity"],
            confidence=last["confidence"],
            reasons=last["reasons"],
            latestAt=last["at"],
        )
        gap["summary"] = _summary(ctx, state, gap, item, last["reasons"], evidence)
    topics = track_topics(state, gaps)
    insights = compute_insights(state, gaps, topics)
    open_n = sum(1 for g in gaps if not g["resolvedAt"])
    ctx.log(AGENT, f"Built evidence for {len(gaps)} gap(s) ({open_n} open) and tracked {len(topics)} topic(s).")
    return {"gaps": gaps, "topic_timeline": topics, "insights": insights}
