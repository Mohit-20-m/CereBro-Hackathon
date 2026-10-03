"""Lightweight language knowledge for code-mixed Indian chats.

The agents use this for two things:
1. Fast language detection (script ranges + romanized marker words), so the
   LLM is only asked to translate messages that actually need it.
2. Heuristic fallbacks, so every agent still produces an answer if the local
   model is unavailable or returns something unusable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

TOKEN_RE = re.compile(r"[a-z']+")

KANNADA_MARKERS = {
    "yaaru", "yaru", "yaaradru", "yaradru", "yaradaru", "madidru", "madidra", "madidira", "madthare",
    "madtare", "madthira", "madthini", "madtini", "maadi", "madi", "maadu", "madbeku", "maadbeku",
    "haudu", "howdu", "alva", "alwa", "idhe", "idya", "aagide", "aagidhe", "agide", "agidhe", "aaytu",
    "aaytha", "aytha", "aitha", "aithu", "aytu", "yenu", "yava", "yaava", "yavaga", "yaavaga", "hege",
    "hegide", "yelli", "beku", "beda", "kalisidra", "kalsidra", "kalsu", "kalisu", "kalsthini", "swalpa",
    "gottilla", "gottu", "saku", "banni", "irli", "nodi", "nodthini", "nodtini", "nodona", "nodkoltini",
    "maga", "macha", "ondu", "yake", "yaake", "aagatte", "agatte", "kodi", "kodthini", "helu", "heli",
    "kelsa", "mugithu", "mugsi", "aagbeku", "ge", "illva", "barthini", "bartini", "hogthini", "gothu",
}
HINDI_MARKERS = {
    "kya", "kisi", "kisne", "bheja", "bhej", "bhejna", "bhejo", "bhejdo", "hai", "hain", "tha", "thi",
    "nahi", "nahin", "haan", "yaar", "kal", "ka", "ki", "ke", "mein", "hoon", "hu", "kaun", "kab",
    "kahan", "kyun", "kyu", "kaise", "deta", "dunga", "karunga", "karo", "kar", "karna", "raha", "rahi",
    "rahe", "abhi", "bhai", "accha", "acha", "theek", "thik", "dekha", "dekh", "dekho", "mast", "chalo",
    "bata", "batao", "pata", "wala", "wali", "kuch", "sab", "aur", "lekin", "phir", "matlab", "samjha",
    "kaam", "bolo", "dekhta", "dekhenge", "baad", "jaldi", "kiya", "kiye", "gaya", "gayi", "hua", "hogi",
}
MALAYALAM_MARKERS = {
    "aarengilum", "arengilum", "ayacho", "ayachu", "ayakku", "ayakkam", "eppo", "eppol", "eppozha",
    "entha", "enthu", "enthanu", "aaru", "aara", "undo", "undu", "alle", "cheyyam", "cheyyu", "cheythu",
    "cheyyano", "sheri", "shari", "ennu", "evide", "evideya", "illallo", "ille", "venam", "venda",
    "nokkam", "nokkatte", "parayu", "paranju", "kazhinju", "aayi", "aano", "machane", "chetta", "njan",
    "ningal", "namukku", "ariyilla", "ready-aano",
}
SHARED_MARKERS = {"illa", "nale", "naale", "sari", "ide"}  # count for both Kannada and Malayalam

COMMON_ENGLISH = set(
    """a about above after again all almost already also always am an and any anyone anything are around as
    ask asked at back be because been before being best better both but by call can cannot check come could
    day did do does doing done dont don't down each else even ever every everyone fine first fix for from
    get give go going good got great guys had has have having he hello help her here hey hi him his how i
    i'll i'm if in into is it it's its just know last later let let's like look lot make me mean meant
    meet meeting more morning most much must my need needs new next no nobody none not nothing now of off
    ok okay on once one only or other our out over please pls ready really right said same see send sent
    she should so some someone something soon still sure take tell than thank thanks that that's the their
    them then there these they thing think this those through time to today tomorrow tonight too try
    under up us use very wait want was we we'll we're well were what what's when where which while who
    whom whose why will with without work working would yeah yes yet you you're your yesterday tonight
    am pm will week night lunch dinner team task tasks file files share shared update updated finish
    finished complete completed start started still anyone everyone again sorry great nice cool true false
    frontend backend api apis database db schema ui ux deploy deployment docker server code bug bugs test
    tests report reports presentation slides ppt doc docs documentation push pushed pull merge branch repo
    github standup sprint design demo login app release build model data query postgresql mongodb sql
    match over last""".split()
)

QUESTION_STARTERS = {
    "who", "what", "when", "where", "why", "how", "which", "whose", "did", "does", "do", "is", "are",
    "can", "could", "will", "would", "should", "has", "have", "anyone", "any", "shall", "was", "were",
}
ROMAN_QUESTION_WORDS = {
    "yaaru", "yaru", "yava", "yaava", "yenu", "hege", "yelli", "yake", "yaake", "yavaga", "kya", "kaun",
    "kab", "kahan", "kyun", "kyu", "kaise", "kisne", "eppo", "eppol", "entha", "enthu", "aaru", "evide",
    "alva", "alle", "undo", "ayacho", "aano", "kalisidra", "madidra",
}
REPEAT_PHRASES = (
    "i asked", "asked about", "asking again", "again", "still no", "still waiting", "anyone?", "no one?",
    "nobody?", "any update", "any updates", "reminder", "phir se", "dobara", "matte", "innu", "ping",
)
CLARIFY_PHRASES = ("i mean", "i meant", "which one", "matlab", "means", "to be clear", "andre", "ennu vechal")
DEFLECT_PHRASES = (
    "i'll check", "ill check", "will check", "let me check", "check later", "later", "let me see",
    "will see", "not sure", "no idea", "idk", "dunno", "dekhta", "dekhenge", "baad mein", "nodthini",
    "nodtini", "nodona", "gottilla", "pata nahi", "ariyilla", "nokkatte", "nokkam", "maybe",
)
PROMISE_PHRASES = (
    "i'll", "i will", "will do", "madthini", "madtini", "kalsthini", "kodthini", "dunga", "karunga",
    "bhej deta", "kar deta", "cheyyam", "ayakkam", "share madthini",
)
ACK_WORDS = {
    "ok", "okay", "k", "kk", "sure", "thanks", "thank", "thx", "yes", "yeah", "yep", "no", "nope",
    "haan", "haudu", "howdu", "sheri", "sari", "done", "cool", "fine", "great", "alright",
}
GREETINGS = {"hi", "hello", "hey", "morning", "good", "gm", "bye", "goodnight", "namaste", "namaskara"}
BARE_REPLIES = {"yes", "yeah", "yep", "no", "nope", "ok", "okay", "sure", "haan", "haudu", "howdu", "illa"}


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


@dataclass
class LanguageResult:
    label: str  # English | Kanglish | Hinglish | Manglish | Kannada | Hindi | Malayalam | Code-mixed
    languages: list[str] = field(default_factory=list)
    script: str = "latin"
    code_mixed: bool = False
    confident: bool = True  # False when the lexicon can't tell; the agent then asks the LLM


def _script_counts(text: str) -> dict[str, int]:
    counts = {"kannada": 0, "devanagari": 0, "malayalam": 0, "latin": 0}
    for ch in text:
        cp = ord(ch)
        if 0x0C80 <= cp <= 0x0CFF:
            counts["kannada"] += 1
        elif 0x0900 <= cp <= 0x097F:
            counts["devanagari"] += 1
        elif 0x0D00 <= cp <= 0x0D7F:
            counts["malayalam"] += 1
        elif ch.isascii() and ch.isalpha():
            counts["latin"] += 1
    return counts


ROMAN_LABEL = {"Kannada": "Kanglish", "Hindi": "Hinglish", "Malayalam": "Manglish"}
NATIVE = {"kannada": "Kannada", "devanagari": "Hindi", "malayalam": "Malayalam"}


def detect_language(text: str) -> LanguageResult:
    counts = _script_counts(text)
    native = [NATIVE[k] for k in ("kannada", "devanagari", "malayalam") if counts[k] > 0]
    toks = tokens(text)

    if native:
        primary = max(native, key=lambda lang: counts[{v: k for k, v in NATIVE.items()}[lang]])
        mixed = counts["latin"] > 0 or len(native) > 1
        langs = native + (["English"] if counts["latin"] else [])
        return LanguageResult(label=primary, languages=langs, script="mixed" if mixed else "native", code_mixed=mixed)

    scores = {"Kannada": 0, "Hindi": 0, "Malayalam": 0}
    english = 0
    for t in toks:
        if t in KANNADA_MARKERS:
            scores["Kannada"] += 1
        if t in HINDI_MARKERS:
            scores["Hindi"] += 1
        if t in MALAYALAM_MARKERS:
            scores["Malayalam"] += 1
        if t in SHARED_MARKERS:
            scores["Kannada"] += 0.5
            scores["Malayalam"] += 0.5
        if t in COMMON_ENGLISH:
            english += 1

    best = max(scores, key=scores.get)
    if scores[best] >= 1:
        ties = [lang for lang, s in scores.items() if s == scores[best]]
        langs = ties + (["English"] if english else [])
        label = ROMAN_LABEL[best] if len(ties) == 1 else "Code-mixed"
        return LanguageResult(label=label, languages=langs, script="latin", code_mixed=bool(english) or len(ties) > 1)

    if not toks:
        return LanguageResult(label="English", languages=["English"], confident=True)
    ratio = english / len(toks)
    confident = ratio >= 0.6 or len(toks) <= 2 and ratio >= 0.5
    return LanguageResult(label="English", languages=["English"], confident=confident)


def label_from_languages(langs: list[str], script: str) -> tuple[str, bool]:
    """Turn the LLM's language list into the label the UI shows."""
    names = [lang.strip().title() for lang in langs if lang and lang.strip()]
    indic = [n for n in names if n in ROMAN_LABEL]
    if not indic:
        return "English", False
    mixed = "English" in names or len(indic) > 1
    if len(indic) > 1:
        return "Code-mixed", True
    if script == "latin":
        return ROMAN_LABEL[indic[0]], mixed
    return indic[0], mixed


def has_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    low = f" {text.lower().strip()} "
    for p in phrases:
        if p.endswith("?"):
            if p in low:
                return True
        elif re.search(rf"(?<![a-z']){re.escape(p)}(?![a-z'])", low):
            return True
    return False


def looks_like_repeat(text: str) -> bool:
    return has_phrase(text, REPEAT_PHRASES)


def looks_like_clarification(text: str) -> bool:
    return has_phrase(text, CLARIFY_PHRASES)


def looks_like_deflection(text: str) -> bool:
    return has_phrase(text, DEFLECT_PHRASES)


def is_bare_reply(text: str) -> bool:
    toks = tokens(text)
    return 0 < len(toks) <= 2 and all(t in BARE_REPLIES for t in toks)


def is_open_question(text: str) -> bool:
    """who/which/what or either-or questions, where a bare yes/no is not an answer."""
    toks = tokens(text)
    return bool(toks) and (
        toks[0] in {"who", "which", "what", "where", "when", "why", "how", "whose"}
        or any(t in {"yaaru", "yava", "yaava", "yenu", "kaun", "kya", "kab", "kahan", "aaru", "entha", "eppo"} for t in toks)
        or " or " in f" {text.lower()} "
    )


def heuristic_intent(text: str, prev_text: str | None = None) -> tuple[str, bool]:
    low = text.lower().strip()
    toks = tokens(text)
    if not toks:
        return "OTHER", False
    if looks_like_repeat(text) and ("?" in text or "asked" in low or "update" in low):
        return "REQUEST", True
    if looks_like_clarification(text):
        return "CLARIFICATION", True
    if low.endswith("?") or toks[0] in QUESTION_STARTERS and len(toks) > 2 or any(t in ROMAN_QUESTION_WORDS for t in toks):
        return "QUESTION", True
    if toks[0] in {"please", "pls", "plz"} or low.startswith(("can you", "could you", "kindly")):
        return "REQUEST", True
    if toks[0] in GREETINGS and len(toks) <= 4:
        return "GREETING", False
    if looks_like_deflection(text) or has_phrase(text, PROMISE_PHRASES):
        return "PROMISE", False
    replying = bool(prev_text and prev_text.strip().endswith("?"))
    if all(t in ACK_WORDS for t in toks):
        return ("ANSWER" if replying else "CONFIRMATION"), False
    if replying and (toks[0] in ACK_WORDS or len(toks) <= 4 and heuristic_topic(text) is None):
        return "ANSWER", False
    return "STATEMENT", False


def starts_with_yes_no(text: str) -> bool:
    toks = tokens(text)
    return bool(toks) and toks[0] in BARE_REPLIES | {"sure", "haan", "nahi", "illa", "yup", "nope"}


def heuristic_topic(text: str) -> str | None:
    """Pick the most specific known subject word in the text."""
    subjects = [
        ("schema", "Database Schema"), ("database", "Database"), ("postgresql", "Database"),
        ("mongodb", "Database"), ("api docs", "API Documentation"), ("api", "API Responsibility"),
        ("backend", "Backend"), ("frontend", "Frontend"), ("ui", "Frontend"), ("deploy", "Deployment"),
        ("docker", "Deployment"), ("report", "Report"), ("ppt", "Presentation"), ("slides", "Presentation"),
        ("presentation", "Presentation"), ("meeting", "Meeting Time"), ("standup", "Standup"),
        ("lunch", "Lunch"), ("match", "Match"), ("test", "Testing"),
    ]
    low = text.lower()
    for word, name in subjects:
        if re.search(rf"(?<![a-z]){re.escape(word)}", low):
            return name
    return None
