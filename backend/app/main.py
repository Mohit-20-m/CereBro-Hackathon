"""ANVAYA backend – Connecting context. Detecting gaps."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .ai.model_manager import model_manager
from .api.routes import router
from .database import models  # noqa: F401  (registers tables)
from .database.connection import Base, SessionLocal, engine, wait_for_db
from .database.models import Conversation, Message
from .database.seed import seed_if_empty
from .services.analysis_service import worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("anvaya")


@asynccontextmanager
async def lifespan(_: FastAPI):
    wait_for_db()
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
        # Anything not analyzed up to its latest message gets queued.
        stale = []
        for conv in db.scalars(select(Conversation)).all():
            latest = db.scalar(select(Message.seq).where(Message.conversation_id == conv.id).order_by(Message.seq.desc()).limit(1)) or 0
            if conv.analysis_status in ("running", "queued"):
                conv.analysis_status = "idle"
            if latest > conv.analyzed_seq or conv.analysis_version == 0:
                stale.append(conv.id)
        db.commit()
    finally:
        db.close()
    model_manager.start()
    worker.start()
    for conv_id in stale:
        worker.enqueue(conv_id)
    log.info("ANVAYA backend ready; %d conversation(s) queued for analysis", len(stale))
    yield


app = FastAPI(title="ANVAYA API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/")
def root():
    return {"name": "ANVAYA", "tagline": "Connecting context. Detecting gaps.", "docs": "/docs"}
