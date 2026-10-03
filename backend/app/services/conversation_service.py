"""Creating conversations, adding messages, importing chat exports and turning
database rows into the JSON the frontend reads."""
from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database.models import Conversation, Message, Participant, utcnow

# ---------------------------------------------------------------------------
# Chat text parsing
# ---------------------------------------------------------------------------
# [Aishu] [10:21]            (ANVAYA test format, text on the next line(s))
BRACKET_HEADER = re.compile(r"^\[(?P<sender>[^\]]+)\]\s*\[(?P<time>\d{1,2}[:.]\d{2}(?:\s?[APap][Mm])?)\]\s*(?P<text>.*)$")
# 12/03/24, 10:21 - Aishu: text   (WhatsApp Android)
ANDROID = re.compile(
    r"^(?P<date>\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}),?\s+(?P<time>\d{1,2}:\d{2}(?::\d{2})?\s?(?:[APap]\.?[Mm]\.?)?)\s+[-–]\s+(?P<sender>[^:]+?):\s(?P<text>.*)$"
)
# [12/03/24, 10:21:05] Aishu: text  (WhatsApp iOS)
IOS = re.compile(
    r"^\u200e?\[(?P<date>\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}),?\s+(?P<time>\d{1,2}:\d{2}(?::\d{2})?\s?(?:[APap]\.?[Mm]\.?)?)\]\s+(?P<sender>[^:]+?):\s(?P<text>.*)$"
)
# Aishu: text
SIMPLE = re.compile(r"^(?P<sender>[A-Za-z\u0080-\uFFFF][\w .'\u0080-\uFFFF-]{0,40}):\s+(?P<text>.+)$")
META = re.compile(r"^#\s*(?P<key>name|title|group|members|participants)\s*:\s*(?P<value>.+)$", re.I)
SKIP = ("<media omitted>", "messages and calls are end-to-end encrypted", "this message was deleted", "image omitted",
        "video omitted", "sticker omitted", "audio omitted", "document omitted", "gif omitted", "null")


def _clean_time(raw: str) -> str:
    raw = raw.strip().replace(".", ":").lower().replace("a:m:", "am").replace("p:m:", "pm")
    m = re.match(r"(\d{1,2}):(\d{2})(?::\d{2})?\s*(am|pm)?", raw)
    if not m:
        return raw[:8]
    hour, minute, ampm = int(m.group(1)), m.group(2), m.group(3)
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute}"


def parse_chat_text(raw: str) -> tuple[str | None, list[str], list[dict]]:
    """Returns (name, members, messages[{sender, time, text}])."""
    name: str | None = None
    members: list[str] = []
    messages: list[dict] = []
    current: dict | None = None
    bracket_mode = False

    def push(entry: dict | None) -> None:
        if entry and entry["text"].strip() and not any(s in entry["text"].lower() for s in SKIP):
            entry["text"] = entry["text"].strip()
            messages.append(entry)

    for line in raw.replace("\r\n", "\n").split("\n"):
        stripped = line.strip().lstrip("\ufeff")
        meta = META.match(stripped)
        if meta:
            if meta.group("key").lower() in ("members", "participants"):
                members = [m.strip() for m in meta.group("value").split(",") if m.strip()]
            else:
                name = meta.group("value").strip()
            continue
        if not stripped:
            continue
        m = BRACKET_HEADER.match(stripped)
        if m:
            push(current)
            bracket_mode = True
            current = {"sender": m.group("sender").strip(), "time": _clean_time(m.group("time")), "text": m.group("text")}
            continue
        m = IOS.match(stripped) or ANDROID.match(stripped)
        if m:
            push(current)
            current = {"sender": m.group("sender").strip(), "time": _clean_time(m.group("time")), "text": m.group("text")}
            continue
        m = None if bracket_mode else SIMPLE.match(stripped)
        if m:
            push(current)
            current = {"sender": m.group("sender").strip(), "time": "", "text": m.group("text")}
            continue
        if current is not None:  # continuation line
            current["text"] = f"{current['text']}\n{stripped}" if current["text"] else stripped
    push(current)

    for msg in messages:
        if msg["sender"] not in members:
            members.append(msg["sender"])
    return name, members, messages


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------
def _clean_names(names: list[str]) -> list[str]:
    out: list[str] = []
    for n in names:
        n = re.sub(r"\s+", " ", (n or "").strip())[:120]
        if n and n.lower() not in {x.lower() for x in out}:
            out.append(n)
    return out


def create_conversation(db: Session, name: str, members: list[str], messages: list[dict] | None = None,
                        source: str = "manual") -> Conversation:
    conv = Conversation(name=name.strip()[:200] or "New group", source=source)
    db.add(conv)
    db.flush()
    for member in _clean_names(members):
        db.add(Participant(conversation_id=conv.id, name=member))
    for i, msg in enumerate(messages or [], start=1):
        db.add(Message(conversation_id=conv.id, seq=i, sender=msg["sender"][:120], content=msg["text"],
                       time_label=msg.get("time") or ""))
    db.commit()
    db.refresh(conv)
    return conv


def add_member(db: Session, conv: Conversation, name: str) -> None:
    name = re.sub(r"\s+", " ", name.strip())[:120]
    if name and name.lower() not in {m.name.lower() for m in conv.members}:
        db.add(Participant(conversation_id=conv.id, name=name))


def add_message(db: Session, conv: Conversation, sender: str, text: str, time_label: str | None) -> Message:
    sender = re.sub(r"\s+", " ", sender.strip())[:120]
    add_member(db, conv, sender)
    next_seq = (db.scalar(select(func.max(Message.seq)).where(Message.conversation_id == conv.id)) or 0) + 1
    msg = Message(conversation_id=conv.id, seq=next_seq, sender=sender, content=text.strip(),
                  time_label=time_label or datetime.now().strftime("%H:%M"))
    db.add(msg)
    conv.updated_at = utcnow()
    db.commit()
    db.refresh(msg)
    return msg


# ---------------------------------------------------------------------------
# Reads / serialization
# ---------------------------------------------------------------------------
def load_conversation(db: Session, conv_id: int) -> Conversation | None:
    return db.scalar(
        select(Conversation)
        .where(Conversation.id == conv_id)
        .options(
            selectinload(Conversation.members),
            selectinload(Conversation.messages).selectinload(Message.analysis),
            selectinload(Conversation.topics),
            selectinload(Conversation.gaps),
        )
    )


def _analysis_info(conv: Conversation, message_count: int) -> dict:
    return {
        "status": conv.analysis_status,
        "stage": conv.analysis_stage,
        "error": conv.analysis_error,
        "mode": conv.analysis_mode,
        "analyzedSeq": conv.analyzed_seq,
        "version": conv.analysis_version,
        "upToDate": conv.analyzed_seq >= message_count and conv.analysis_status not in ("queued", "running"),
    }


def serialize_message(m: Message) -> dict:
    out = {"id": m.seq, "sender": m.sender, "time": m.time_label, "text": m.content}
    a = m.analysis
    if a:
        if a.intent:
            out["intent"] = a.intent
        if a.language_label and a.language_label != "English":
            out["lang"] = a.language_label
            if a.normalized_text and a.normalized_text.strip() != m.content.strip():
                out["normalized"] = a.normalized_text
        if a.topic_name:
            out["topic"] = a.topic_name
    return out


def serialize_gap(g) -> dict:
    return {
        "id": g.key,
        "topic": g.topic_name,
        "topicKey": g.topic_key,
        "raisedBy": g.raised_by,
        "questionAt": g.question_seq,
        "resolvedAt": g.resolved_seq,
        "summary": g.summary,
        "critic": g.critic,
        "stages": g.stages,
        "evidence": [{"id": e.message_seq, "role": e.role, "note": e.note} for e in g.evidence],
    }


def serialize_conversation(conv: Conversation) -> dict:
    count = len(conv.messages)
    return {
        "id": conv.id,
        "type": conv.kind,
        "name": conv.name,
        "source": conv.source,
        "members": [m.name for m in conv.members],
        "messages": [serialize_message(m) for m in conv.messages],
        "gaps": [serialize_gap(g) for g in conv.gaps],
        "topics": [{"key": t.key, "name": t.name, "status": t.status, "timeline": t.timeline} for t in conv.topics],
        "insights": conv.insights or {},
        "agentTrace": conv.agent_trace or [],
        "analysis": _analysis_info(conv, count),
    }


def list_conversations(db: Session) -> list[dict]:
    convs = db.scalars(
        select(Conversation).options(selectinload(Conversation.members), selectinload(Conversation.gaps))
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
    ).all()
    out = []
    for c in convs:
        last = db.scalar(select(Message).where(Message.conversation_id == c.id).order_by(Message.seq.desc()).limit(1))
        count = db.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id)) or 0
        out.append({
            "id": c.id,
            "type": c.kind,
            "name": c.name,
            "members": [m.name for m in c.members],
            "messageCount": count,
            "lastMessage": {"sender": last.sender, "text": last.content, "time": last.time_label} if last else None,
            "openGaps": sum(1 for g in c.gaps if g.status == "unresolved"),
            "analysis": _analysis_info(c, count),
        })
    return out
