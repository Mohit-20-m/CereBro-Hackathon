"""REST API used by the frontend."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ai.model_manager import model_manager
from ..config import settings
from ..agents.gap_detector import GAP_LABELS, WEIGHTS
from ..database.connection import get_db
from ..database.models import Conversation
from ..services import conversation_service as svc
from ..services.analysis_service import worker

router = APIRouter(prefix="/api")


class ConversationIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    members: list[str] = Field(default_factory=list)


class MessageIn(BaseModel):
    sender: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=4000)
    time: str | None = Field(default=None, max_length=16)


class MemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


def _get(db: Session, conv_id: int) -> Conversation:
    conv = svc.load_conversation(db, conv_id)
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "ai": model_manager.snapshot()}


@router.get("/meta")
def meta():
    return {
        "app": {"name": "ANVAYA", "tagline": "Connecting context. Detecting gaps."},
        "signals": [
            {"key": "unanswered", "label": "Unanswered question", "weight": WEIGHTS["unanswered"]},
            {"key": "repeated", "label": "Repeated request", "weight": WEIGHTS["repeated"]},
            {"key": "recurrence", "label": "Topic recurrence", "weight": WEIGHTS["recurrence"]},
            {"key": "clarification", "label": "Clarification", "weight": WEIGHTS["clarification"]},
        ],
        "gapTypes": GAP_LABELS,
        "severity": {"possible": 0.3, "strong": 0.6},
        "models": {"embeddings": settings.embed_model, "nli": settings.nli_model,
                   "llm": settings.llm_model if settings.ollama_url else None},
        "agents": ["Language Analyzer", "Intent Analyzer", "Topic Analyzer", "Response Matcher", "Investigator",
                   "Gap Detector", "Critic", "Evidence Generator"],
    }


@router.get("/conversations")
def conversations(db: Session = Depends(get_db)):
    return svc.list_conversations(db)


@router.post("/conversations", status_code=201)
def create(body: ConversationIn, db: Session = Depends(get_db)):
    if not [m for m in body.members if m.strip()]:
        raise HTTPException(422, "Add at least one member")
    conv = svc.create_conversation(db, body.name, body.members)
    return svc.serialize_conversation(_get(db, conv.id))


@router.post("/conversations/import", status_code=201)
async def import_chat(file: UploadFile = File(...), name: str | None = Form(default=None), db: Session = Depends(get_db)):
    raw = await file.read()
    if len(raw) > 5_000_000:
        raise HTTPException(413, "File is larger than 5 MB")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("latin-1")
    parsed_name, members, messages = svc.parse_chat_text(content)
    if not messages:
        raise HTTPException(422, "No messages found. Use lines like '[Name] [10:21]' followed by text, "
                                 "'Name: text', or a WhatsApp export.")
    title = (name or "").strip() or parsed_name or (file.filename or "Imported chat").rsplit(".", 1)[0]
    conv = svc.create_conversation(db, title, members, messages, source=f"import:{file.filename}")
    worker.enqueue(conv.id)
    return svc.serialize_conversation(_get(db, conv.id))


@router.get("/conversations/{conv_id}")
def get_conversation(conv_id: int, db: Session = Depends(get_db)):
    return svc.serialize_conversation(_get(db, conv_id))


@router.delete("/conversations/{conv_id}", status_code=204)
def delete_conversation(conv_id: int, db: Session = Depends(get_db)):
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    db.delete(conv)
    db.commit()


@router.post("/conversations/{conv_id}/members", status_code=201)
def add_member(conv_id: int, body: MemberIn, db: Session = Depends(get_db)):
    conv = _get(db, conv_id)
    svc.add_member(db, conv, body.name)
    db.commit()
    return svc.serialize_conversation(_get(db, conv_id))


@router.post("/conversations/{conv_id}/messages", status_code=201)
def send_message(conv_id: int, body: MessageIn, db: Session = Depends(get_db)):
    conv = _get(db, conv_id)
    msg = svc.add_message(db, conv, body.sender, body.text, body.time)
    worker.enqueue(conv_id)
    return {"message": {"id": msg.seq, "sender": msg.sender, "time": msg.time_label, "text": msg.content}}


@router.post("/conversations/{conv_id}/analyze", status_code=202)
def analyze(conv_id: int, db: Session = Depends(get_db)):
    _get(db, conv_id)
    worker.enqueue(conv_id)
    return {"queued": True}


@router.get("/conversations/{conv_id}/gaps")
def gaps(conv_id: int, db: Session = Depends(get_db)):
    return svc.serialize_conversation(_get(db, conv_id))["gaps"]


@router.get("/conversations/{conv_id}/topics")
def topics(conv_id: int, db: Session = Depends(get_db)):
    return svc.serialize_conversation(_get(db, conv_id))["topics"]


@router.get("/conversations/{conv_id}/insights")
def insights(conv_id: int, db: Session = Depends(get_db)):
    data = svc.serialize_conversation(_get(db, conv_id))
    return {"insights": data["insights"], "analysis": data["analysis"], "agentTrace": data["agentTrace"]}
