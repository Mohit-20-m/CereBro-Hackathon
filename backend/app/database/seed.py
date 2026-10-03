"""On first start, load every .txt chat in DATA_DIR as a normal conversation.
Nothing about these chats is special afterwards: the agents analyze them
exactly like a chat you import or type yourself."""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..services.conversation_service import create_conversation, parse_chat_text
from .models import Conversation

log = logging.getLogger("anvaya.seed")


def seed_if_empty(db: Session) -> list[int]:
    if (db.scalar(select(func.count(Conversation.id))) or 0) > 0:
        return []
    folder = Path(settings.data_dir)
    if not folder.is_dir():
        log.info("No data folder at %s; starting empty.", folder)
        return []
    created = []
    for path in sorted(folder.glob("*.txt")):
        try:
            name, members, messages = parse_chat_text(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            log.warning("Skipping %s: %s", path.name, exc)
            continue
        if not messages:
            continue
        title = name or path.stem.replace("_", " ").replace("-", " ").title()
        conv = create_conversation(db, title, members, messages, source=f"file:{path.name}")
        created.append(conv.id)
        log.info("Loaded %s (%d messages)", title, len(messages))
    return created
