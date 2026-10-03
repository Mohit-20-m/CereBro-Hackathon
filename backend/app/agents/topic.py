"""Agent 3 – Topic Analyzer.

Finds what each message is about with embedding-based keyphrase extraction:
it lists the content phrases in the message and keeps the one closest in
meaning to the whole message. Phrases are merged into the conversation's
existing topics by embedding similarity, so "schema" asked in Kanglish and
"database schema" in English land on the same topic. Short replies ("yes",
"I'll check") inherit the topic of the message they answer.
"""
from __future__ import annotations

import re

from ..ai.lexicon import heuristic_topic
from ..ml.embeddings import HASH_MODEL, cosine, embed_texts, thresholds
from .context import AgentContext

AGENT = "Topic Analyzer"

STOPWORDS = set("""
a an the is are was were be been being am i you he she it we they me my your our their this that these those
to of in on at for with from by about as and or but if so then than too very just also still already almost
who what when where which why how whose whom anyone someone everyone anybody somebody nobody no yes not
do did does done doing will would shall should can could may might must have has had get got go going gone
guys guy team all any some one ok okay sure thanks thank please pls hi hello hey morning night good bye
send sent sending share shared check checked update updated handle handling complete completed finish finished
ready make made take took give gave tell told ask asked asking again right really actually i'll i'm let's
tonight today tomorrow yesterday later now soon min mins minutes hour hours time last over first next
fix fixed work works working using use used mean meant need needs want great nice cool fine done watched
see look looking join come coming there here yet sir maam bro dude yaar re
submit submitted after before during while meet let lets works worked watch like love think thought say said
know knew maybe around two three four five back stuff thing things way done? talk talked plan planned
""".split())
WORD = re.compile(r"[A-Za-z][A-Za-z0-9+#.'\-]*")


def _candidates(text: str, names: set[str]) -> list[str]:
    runs, current = [], []
    for raw in WORD.findall(text):
        word = raw.strip(".-'")
        if not word or "'" in word or word.lower() in STOPWORDS or word.lower() in names or len(word) < 2:
            if current:
                runs.append(current)
            current = []
        else:
            current.append(word)
    if current:
        runs.append(current)
    cands = []
    for run in runs:
        cands += run
        cands += [f"{a} {b}" for a, b in zip(run, run[1:])]
    seen, out = set(), []
    for c in cands:
        if c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out[:8]


def _title(phrase: str) -> str:
    words = []
    for w in phrase.split():
        words.append(w.upper() if len(w) <= 3 and w.isalpha() and w.lower() not in {"bug", "app", "day"} else
                     (w if any(ch.isupper() for ch in w[1:]) else w[:1].upper() + w[1:]))
    return " ".join(words)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "topic"


def topic_agent(ctx: AgentContext, state: dict) -> dict:
    ctx.stage(AGENT)
    analyses = state["analyses"]
    msgs = state["messages"]
    registry: dict[str, str] = dict(state.get("topics") or {})
    names = {m["sender"].lower() for m in msgs}
    name_vec: dict[str, list[float]] = {}
    new_topics: list[str] = []
    todo = [i for i, m in enumerate(msgs) if not analyses[m["seq"]].get("topic_done")]

    def vec_of(phrases: list[str]) -> list[list[float]]:
        missing = [p for p in phrases if p not in name_vec]
        if missing:
            vectors, _ = embed_texts(missing)
            name_vec.update(zip(missing, vectors))
        return [name_vec[p] for p in phrases]

    def canonical(phrase: str, model: str | None) -> tuple[str, str]:
        name = _title(phrase)
        for key, existing in registry.items():
            if existing.lower() == name.lower():
                return key, existing
        if registry:
            keys = list(registry)
            vecs = vec_of([name] + [registry[k] for k in keys])
            sims = [cosine(vecs[0], v) for v in vecs[1:]]
            best = max(range(len(keys)), key=lambda j: sims[j])
            if sims[best] >= thresholds(model)["topic_merge"]:
                return keys[best], registry[keys[best]]
        key = _slug(name)
        while key in registry:
            key += "-2"
        registry[key] = name
        new_topics.append(name)
        return key, name

    for i in todo:
        m = msgs[i]
        a = analyses[m["seq"]]
        text = a.get("normalized") or m["text"]
        intent = a.get("intent")
        model = a.get("embed_model")
        key = name = None
        source = "none"

        cands = [] if intent == "GREETING" else _candidates(text, names)
        if cands and model != HASH_MODEL:
            vecs = vec_of(cands)
            scored = sorted(((cosine(a.get("embedding"), v), c) for c, v in zip(cands, vecs)), reverse=True)
            key, name = canonical(scored[0][1], model)
            source = f"keyphrase {scored[0][0]:.2f}"
        elif cands:
            phrase = heuristic_topic(text) or cands[0]
            key, name = canonical(phrase, model)
            source = "rules"
        elif intent in {"ANSWER", "CONFIRMATION", "PROMISE"} and i > 0:
            prev = next((msgs[j] for j in range(i - 1, -1, -1) if msgs[j]["sender"] != m["sender"]), None)
            if prev and analyses[prev["seq"]].get("topic_key"):
                key = analyses[prev["seq"]]["topic_key"]
                name = registry.get(key)
                source = f"inherited from #{prev['seq']}"

        a.update(topic_key=key, topic_name=name, topic_done=True)
        a.setdefault("sources", {})["topic"] = source

    ctx.save_analyses(state, [msgs[i]["seq"] for i in todo])
    if todo:
        found = f" New topics: {', '.join(new_topics)}." if new_topics else ""
        ctx.log(AGENT, f"Mapped {len(todo)} message(s) to {len(registry)} topic(s) using keyphrase embeddings.{found}")
    return {"analyses": analyses, "topics": registry}
