"""Romanized Kannada / Hindi / Malayalam → English word mapping.

The multilingual embedding model was trained on native scripts, not on chat
written in Latin letters. Mapping the most common romanized function words
("yaaru" → who, "kisi" → anyone) lets the model read "schema yaaru send
madidru?" as "schema who send did?", which it understands well. Only applied
to messages the Language Analyzer marked as non-English.
"""
from __future__ import annotations

import re

KANNADA = {
    "yaaru": "who", "yaru": "who", "yaaradru": "anyone", "yaradru": "anyone", "yaradaru": "anyone",
    "madidru": "did", "madidra": "did", "madidira": "did", "madthare": "will do", "madtare": "will do",
    "madthira": "will you do", "madthini": "I will do", "madtini": "I will do", "maadi": "do", "madi": "do",
    "maadu": "do", "madbeku": "must do", "maadbeku": "must do", "haudu": "yes", "howdu": "yes",
    "alva": "right?", "alwa": "right?", "idhe": "is there", "ide": "is", "idya": "is it there",
    "aagide": "is done", "aagidhe": "is done", "agide": "is done", "agidhe": "is done", "aaytu": "done",
    "aytu": "done", "aaytha": "done?", "aytha": "done?", "aitha": "done?", "aithu": "done",
    "yenu": "what", "enu": "what", "yava": "which", "yaava": "which", "yavaga": "when", "yaavaga": "when",
    "hege": "how", "hegide": "how is it", "yelli": "where", "beku": "need", "beda": "not needed",
    "kalisidra": "did you send", "kalsidra": "did you send", "kalsu": "send", "kalisu": "send",
    "kalsthini": "I will send", "swalpa": "a little", "gottilla": "don't know", "gottu": "know",
    "nodi": "see", "nodthini": "I will check", "nodtini": "I will check", "nodona": "let's see",
    "ondu": "one", "yake": "why", "yaake": "why", "aagatte": "will happen", "agatte": "will happen",
    "kodi": "give", "kodthini": "I will give", "helu": "tell", "heli": "tell", "kelsa": "work",
    "mugithu": "finished", "mugsi": "finish", "barthini": "I will come", "illva": "isn't it",
    "ge": "", "maga": "", "macha": "", "guru": "",
}
HINDI = {
    "kya": "what", "kisi": "anyone", "kisne": "who", "ne": "", "bheja": "sent", "bhej": "send",
    "bhejna": "to send", "bhejo": "send", "bhejdo": "send it", "tha": "was", "thi": "was", "hai": "is",
    "hain": "are", "nahi": "no", "nahin": "no", "haan": "yes", "yaar": "", "kal": "yesterday",
    "ka": "", "ki": "", "ke": "", "mein": "in", "main": "I", "hoon": "am", "hu": "am", "kaun": "who",
    "kab": "when", "kahan": "where", "kyun": "why", "kyu": "why", "kaise": "how", "deta": "will",
    "dunga": "will give", "karunga": "will do", "karo": "do", "kar": "do", "karna": "to do",
    "raha": "doing", "rahi": "doing", "abhi": "now", "bhai": "", "accha": "okay", "acha": "okay",
    "theek": "fine", "thik": "fine", "dekha": "watched", "dekh": "see", "dekho": "see", "mast": "great",
    "chalo": "okay", "bata": "tell", "batao": "tell", "pata": "know", "kuch": "something", "sab": "all",
    "aur": "and", "lekin": "but", "phir": "again", "matlab": "I mean", "kaam": "work", "bolo": "tell",
    "dekhta": "I will check", "dekhenge": "will see", "baad": "after", "jaldi": "quickly", "kiya": "did",
    "gaya": "went", "hua": "happened", "hogi": "will be",
}
MALAYALAM = {
    "aarengilum": "anyone", "arengilum": "anyone", "ayacho": "sent?", "ayachu": "sent", "ayakku": "send",
    "ayakkam": "I will send", "eppo": "when", "eppol": "when", "entha": "what", "enthu": "what",
    "enthanu": "what is", "aaru": "who", "aara": "who", "undo": "is there", "undu": "there is",
    "alle": "right?", "cheyyam": "I will do", "cheyyu": "do", "cheythu": "did", "sheri": "okay",
    "shari": "okay", "evide": "where", "illa": "no", "ille": "isn't it", "venam": "need",
    "venda": "not needed", "nokkam": "I will check", "nokkatte": "let me check", "parayu": "tell",
    "kazhinju": "finished", "aayi": "done", "njan": "I", "namukku": "we", "ariyilla": "don't know",
    "nale": "tomorrow", "naale": "tomorrow",
}
SHARED = {"nale": "tomorrow", "naale": "tomorrow", "illa": "no", "sari": "okay"}

_BY_LABEL = {
    "Kanglish": {**MALAYALAM, **HINDI, **KANNADA},
    "Hinglish": {**KANNADA, **MALAYALAM, **HINDI},
    "Manglish": {**KANNADA, **HINDI, **MALAYALAM},
}
_ALL = {**HINDI, **MALAYALAM, **KANNADA, **SHARED}
_WORD = re.compile(r"[A-Za-z']+|[^A-Za-z']+")


# Verb constructions: "<english verb> madthini" → "I will <verb>", etc.
_PATTERNS = [
    (re.compile(r"\b([A-Za-z]+)\s+(?:madthini|madtini|maadthini|cheyyam)\b", re.I), r"I will \1"),
    (re.compile(r"\b([A-Za-z]+)\s+(?:madthare|madtare|maadthare)\b", re.I), r"will \1"),
    (re.compile(r"\b([A-Za-z]+)\s+(?:madidru|madidra|madidira|maadidru|cheythu)\b", re.I), r"did \1"),
    (re.compile(r"\bbhej\s+(?:deta|deti|dunga|dungi|denge)(?:\s+(?:hoon|hu|hain))?\b", re.I), "will send"),
    (re.compile(r"\bkar\s+(?:deta|deti|dunga|dungi|denge)(?:\s+(?:hoon|hu|hain))?\b", re.I), "will do"),
    (re.compile(r"\b(?:bhej\s+diya|bheja\s+hai)\b", re.I), "sent"),
    (re.compile(r"\bkar\s+diya\b", re.I), "did it"),
    (re.compile(r"\b(\d+\s*[A-Za-z]+)\s+mein\b", re.I), r"in \1"),
    (re.compile(r"\bkya\s*\?", re.I), "?"),
    (re.compile(r"\b(\d+)\s+ge\b", re.I), r"at \1"),
]


def normalize(text: str, label: str) -> str:
    table = _BY_LABEL.get(label, _ALL)
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    out = []
    for part in _WORD.findall(text):
        low = part.lower()
        if low in table:
            out.append(table[low])
        else:
            out.append(part)
    result = re.sub(r"\s+", " ", "".join(out)).strip()
    result = re.sub(r"\s+([?.!,])", r"\1", result)
    return re.sub(r"([?!.])\1+", r"\1", result)
