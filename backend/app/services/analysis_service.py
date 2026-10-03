"""Background analysis worker.

New messages are stored immediately; the worker then runs the LangGraph agent
pipeline for that conversation and saves topics, gaps, evidence, insights and
the agent activity trace. Work for one conversation is never run twice at the
same time, and if messages arrive mid-run the conversation is queued again.
"""
from __future__ import annotations

import logging
import queue
import threading
import traceback

from sqlalchemy import delete, func, select

from ..ai.model_manager import model_manager
from ..agents.context import AgentContext
from ..agents.graph import build_graph
from ..database.connection import SessionLocal
from ..database.models import CommunicationGap, Conversation, GapEvidence, Message, Topic

log = logging.getLogger("anvaya.analysis")


def _initial_state(db, conv: Conversation) -> dict:
    rows = db.scalars(select(Message).where(Message.conversation_id == conv.id).order_by(Message.seq)).all()
    messages, analyses, topics = [], {}, {}
    for m in rows:
        messages.append({"seq": m.seq, "db_id": m.id, "sender": m.sender, "text": m.content, "time": m.time_label})
        a = m.analysis
        if a:
            analyses[m.seq] = {
                "language_label": a.language_label, "languages": a.languages, "script": a.script,
                "is_code_mixed": a.is_code_mixed, "normalized": a.normalized_text, "intent": a.intent,
                "requires_response": a.requires_response, "topic_done": a.topic_done, "topic_key": a.topic_key,
                "topic_name": a.topic_name, "embedding": a.embedding, "embed_model": a.embed_model,
                "sources": a.sources or {},
            }
            if a.topic_key and a.topic_name:
                topics[a.topic_key] = a.topic_name
        else:
            analyses[m.seq] = {"sources": {}}
    return {"conversation_id": conv.id, "messages": messages, "analyses": analyses, "topics": topics,
            "pending": None, "items": [], "current": None, "gaps": [], "critic_queue": []}


def _persist(db, conv: Conversation, final: dict) -> None:
    db.execute(delete(Topic).where(Topic.conversation_id == conv.id))
    old = db.scalars(select(CommunicationGap.id).where(CommunicationGap.conversation_id == conv.id)).all()
    if old:
        db.execute(delete(GapEvidence).where(GapEvidence.gap_id.in_(old)))
        db.execute(delete(CommunicationGap).where(CommunicationGap.id.in_(old)))

    for t in final.get("topic_timeline") or []:
        db.add(Topic(conversation_id=conv.id, key=t["key"], name=t["name"], status=t["status"],
                     first_seq=t["first"], last_seq=t["last"], timeline=t["timeline"]))
    for g in final.get("gaps") or []:
        stages = [
            {"at": s["at"], "type": s["type"], "signals": s["signals"], "score": s["score"],
             "severity": s["severity"], "confidence": s["confidence"], "reasons": s["reasons"]}
            for s in g["stages"]
        ]
        row = CommunicationGap(
            conversation_id=conv.id, key=g["id"], topic_key=g["topicKey"], topic_name=g["topic"][:120],
            gap_type=g["type"], raised_by=g["raisedBy"], question_seq=g["q_seq"], latest_seq=g["latestAt"],
            score=g["score"], severity=g["severity"], confidence=g["confidence"],
            status="resolved" if g["resolvedAt"] else "unresolved", resolved_seq=g["resolvedAt"],
            signals=g["signals"], reasons=g["reasons"], stages=stages, summary=g.get("summary"),
            critic=g.get("critic") or {},
        )
        db.add(row)
        db.flush()
        for pos, e in enumerate(g["evidence"]):
            db.add(GapEvidence(gap_id=row.id, message_seq=e["id"], role=e["role"], note=e.get("note"), position=pos))
    conv.insights = final.get("insights") or {}


def run_analysis(conv_id: int) -> int:
    """Runs the agent graph once. Returns the highest message seq analyzed."""
    db = SessionLocal()
    try:
        conv = db.get(Conversation, conv_id)
        if conv is None:
            return 0
        conv.analysis_status, conv.analysis_error, conv.analysis_stage = "running", None, "Starting"
        db.commit()

        state = _initial_state(db, conv)
        upto = state["messages"][-1]["seq"] if state["messages"] else 0
        ctx = AgentContext(db, conv)
        if state["messages"]:
            ctx.log("Orchestrator", f"Analysis started for {len(state['messages'])} message(s) "
                                    f"in {model_manager.mode} mode.")
            final = build_graph(ctx).invoke(state, {"recursion_limit": 2000})
            ctx.log("Orchestrator", f"Finished with {ctx.llm.calls} model call(s).")
        else:
            final = {"topic_timeline": [], "gaps": [], "insights": {}}
        _persist(db, conv, final)
        conv.agent_trace = ctx.trace[-120:]
        conv.analysis_mode = model_manager.mode
        conv.analyzed_seq = upto
        conv.analysis_version += 1
        conv.analysis_status, conv.analysis_stage = "idle", None
        db.commit()
        return upto
    except Exception as exc:  # noqa: BLE001
        log.error("Analysis failed for %s: %s\n%s", conv_id, exc, traceback.format_exc())
        db.rollback()
        conv = db.get(Conversation, conv_id)
        if conv:
            conv.analysis_status, conv.analysis_stage = "error", None
            conv.analysis_error = str(exc)[:500]
            db.commit()
        return -1
    finally:
        db.close()


class AnalysisWorker:
    def __init__(self) -> None:
        self._queue: "queue.Queue[int]" = queue.Queue()
        self._pending: set[int] = set()
        self._lock = threading.Lock()

    def start(self) -> None:
        threading.Thread(target=self._loop, name="analysis-worker", daemon=True).start()

    def enqueue(self, conv_id: int) -> None:
        with self._lock:
            if conv_id in self._pending:
                return
            self._pending.add(conv_id)
        db = SessionLocal()
        try:
            conv = db.get(Conversation, conv_id)
            if conv and conv.analysis_status != "running":
                conv.analysis_status = "queued"
                db.commit()
        finally:
            db.close()
        self._queue.put(conv_id)

    def _loop(self) -> None:
        model_manager.settled.wait()  # don't analyze while models are still downloading
        while True:
            conv_id = self._queue.get()
            with self._lock:
                self._pending.discard(conv_id)
            upto = run_analysis(conv_id)
            if upto >= 0:
                db = SessionLocal()
                try:
                    latest = db.scalar(select(func.max(Message.seq)).where(Message.conversation_id == conv_id)) or 0
                finally:
                    db.close()
                if latest > upto:
                    self.enqueue(conv_id)


worker = AnalysisWorker()
