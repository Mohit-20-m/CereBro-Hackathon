"""Agent 1 – Language Analyzer.

Detects script, languages and code-mixing for each new message (alphabet
ranges plus romanized marker words). Romanized Kannada / Hindi / Malayalam is
normalized into English words so the multilingual embedding model can read it;
the original text is always kept for display. Then every message is embedded
with paraphrase-multilingual-MiniLM-L12-v2.
"""
from __future__ import annotations

from ..ai.lexicon import detect_language
from ..ml.embeddings import current_embed_model, embed_texts
from ..ml.romanized import normalize
from .context import AgentContext

AGENT = "Language Analyzer"


def language_agent(ctx: AgentContext, state: dict) -> dict:
    ctx.stage(AGENT)
    analyses = state["analyses"]
    todo = [m for m in state["messages"] if not analyses.get(m["seq"], {}).get("language_label")]
    non_english, mixed = 0, 0

    for m in todo:
        det = detect_language(m["text"])
        a = analyses.setdefault(m["seq"], {"sources": {}})
        if det.label in ("Kanglish", "Hinglish", "Manglish", "Code-mixed"):
            normalized, source = normalize(m["text"], det.label), "romanized-normalizer"
        else:
            normalized, source = m["text"], "native" if det.script != "latin" else "english"
        non_english += int(det.label != "English")
        mixed += int(det.code_mixed)
        a.update(language_label=det.label, languages=det.languages, script=det.script,
                 is_code_mixed=det.code_mixed, normalized=normalized)
        a.setdefault("sources", {})["language"] = source

    model = current_embed_model()
    need = [m["seq"] for m in state["messages"]
            if not analyses[m["seq"]].get("embedding") or analyses[m["seq"]].get("embed_model") != model]
    if need:
        vectors, used = embed_texts([analyses[s]["normalized"] for s in need])
        for s, v in zip(need, vectors):
            analyses[s]["embedding"] = v
            analyses[s]["embed_model"] = used

    ctx.save_analyses(state, sorted({m["seq"] for m in todo} | set(need)))
    if todo:
        ctx.log(AGENT, f"Read {len(todo)} new message(s): {non_english} non-English, {mixed} code-mixed. "
                       f"Embedded {len(need)} with {model.split('/')[-1]}.")
    return {"analyses": analyses}
