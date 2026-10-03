"""Agent 2 – Intent Analyzer.

Labels each message by comparing its embedding with example phrases for every
intent (nearest meaning wins). When that comparison is not confident, it asks
the mDeBERTa NLI model to classify the message zero-shot. Only if neither model
is available does it use simple rules.
"""
from __future__ import annotations

from ..ai.lexicon import heuristic_intent, looks_like_clarification, looks_like_repeat
from ..ml.embeddings import HASH_MODEL, cosine, current_embed_model, embed_texts
from ..ml.engine import engine
from ..ml.prototypes import INTENT_EXAMPLES, NLI_INTENT_LABELS
from .context import AgentContext

AGENT = "Intent Analyzer"
NEEDS_REPLY = {"QUESTION", "REQUEST", "CLARIFICATION"}
CONFIDENT_SCORE = 0.55
CONFIDENT_MARGIN = 0.06

_protos: dict = {"model": None, "items": []}


def _prototypes() -> list[tuple[str, list[float]]]:
    model = current_embed_model()
    if _protos["model"] != model:
        labels = [(intent, text) for intent, texts in INTENT_EXAMPLES.items() for text in texts]
        vectors, _ = embed_texts([t for _, t in labels])
        _protos.update(model=model, items=[(intent, v) for (intent, _), v in zip(labels, vectors)])
    return _protos["items"]


def _embedding_scores(vec: list[float], has_question_mark: bool) -> list[tuple[str, float]]:
    by_intent: dict[str, list[float]] = {}
    for intent, pv in _prototypes():
        by_intent.setdefault(intent, []).append(cosine(vec, pv))
    scores = {}
    for intent, sims in by_intent.items():
        top = sorted(sims, reverse=True)[:2]
        scores[intent] = sum(top) / len(top)
        if has_question_mark and intent in NEEDS_REPLY:
            scores[intent] += 0.05
    return sorted(scores.items(), key=lambda kv: -kv[1])


def classify(text: str, vec: list[float] | None, prev_text: str | None) -> tuple[str, str]:
    if not engine.embed_ok or not vec or current_embed_model() == HASH_MODEL:
        intent, _ = heuristic_intent(text, prev_text)
        return intent, "rules"
    ranked = _embedding_scores(vec, "?" in text)
    (best, score), (_, second) = ranked[0], ranked[1]
    if score >= CONFIDENT_SCORE and score - second >= CONFIDENT_MARGIN:
        return best, f"embedding {score:.2f}"
    if engine.nli_ok:
        premise = f"{prev_text}\n{text}" if prev_text else text
        z = engine.classify(premise if len(text.split()) <= 3 else text, list(NLI_INTENT_LABELS), "This message is {}.")
        label, p = max(z.items(), key=lambda kv: kv[1])
        if p >= 0.35:
            return NLI_INTENT_LABELS[label], f"nli {p:.2f}"
    return best, f"embedding {score:.2f} (low confidence)"


def intent_agent(ctx: AgentContext, state: dict) -> dict:
    ctx.stage(AGENT)
    analyses = state["analyses"]
    msgs = state["messages"]
    todo = [i for i, m in enumerate(msgs) if not analyses[m["seq"]].get("intent")]
    counts: dict[str, int] = {}
    used_nli = 0

    for i in todo:
        m = msgs[i]
        a = analyses[m["seq"]]
        prev = msgs[i - 1] if i > 0 else None
        text = a.get("normalized") or m["text"]
        prev_text = AgentContext.meaning(state, prev["seq"]) if prev else None
        intent, source = classify(text, a.get("embedding"), prev_text)
        used_nli += int(source.startswith("nli"))

        # Light guard rails for explicit re-asks by the same person.
        earlier_q = any(analyses[p["seq"]].get("requires_response") and p["sender"] == m["sender"] for p in msgs[:i])
        combined = f"{m['text']} {text}"
        if earlier_q and looks_like_repeat(combined) and intent not in NEEDS_REPLY:
            intent, source = "REQUEST", source + " + re-ask"
        elif earlier_q and looks_like_clarification(combined) and intent in {"QUESTION", "STATEMENT"}:
            intent, source = "CLARIFICATION", source + " + clarify"

        a.update(intent=intent, requires_response=intent in NEEDS_REPLY)
        a.setdefault("sources", {})["intent"] = source
        counts[intent] = counts.get(intent, 0) + 1

    ctx.save_analyses(state, [msgs[i]["seq"] for i in todo])
    if todo:
        summary = ", ".join(f"{v} {k.lower()}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
        nli = f" Asked the NLI model about {used_nli} unclear one(s)." if used_nli else ""
        ctx.log(AGENT, f"Classified {len(todo)} message(s): {summary}.{nli}")
    return {"analyses": analyses}
