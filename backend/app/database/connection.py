import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ..config import settings

log = logging.getLogger("anvaya.db")


class Base(DeclarativeBase):
    pass


_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def wait_for_db(retries: int = 40, delay: float = 2.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001
            log.info("Waiting for database (%s/%s): %s", attempt, retries, exc)
            time.sleep(delay)
    raise RuntimeError("Database is not reachable")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
