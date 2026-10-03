"""Loads the local transformer models and (optionally) connects to an LLM.

state:  loading  → ready       (embeddings + NLI loaded; agents use them)
                 → heuristic   (models unavailable or AI_ENABLED=false; rule fallback)
llm:    disabled | connecting | downloading | ready | unavailable   (optional add-on)
"""
from __future__ import annotations

import json
import logging
import threading
import time

import httpx

from ..config import settings
from ..ml.engine import engine

log = logging.getLogger("anvaya.models")


class ModelManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.settled = threading.Event()
        self.state = "loading"
        self.message = "Loading the language models"
        self.llm_state = "connecting" if settings.ollama_url else "disabled"
        self.llm_percent = 0
        self.llm_ok = False

    def start(self) -> None:
        threading.Thread(target=self._load_ml, name="ml-loader", daemon=True).start()
        if settings.ollama_url and settings.ai_enabled:
            threading.Thread(target=self._connect_llm, name="llm-connector", daemon=True).start()

    @property
    def ml_ok(self) -> bool:
        return engine.embed_ok

    @property
    def mode(self) -> str:
        if not engine.embed_ok:
            return "heuristic"
        return "ml+llm" if self.llm_ok else "ml"

    def snapshot(self) -> dict:
        with self._lock:
            models = {
                settings.embed_model: {"status": "ready" if engine.embed_ok else self._status()},
            }
            if settings.nli_enabled:
                models[settings.nli_model] = {"status": "ready" if engine.nli_ok else self._status()}
            return {
                "state": self.state,
                "message": self.message,
                "mode": self.mode,
                "embedModel": settings.embed_model,
                "nliModel": settings.nli_model if engine.nli_ok else None,
                "llmModel": settings.llm_model if settings.ollama_url else None,
                "llmState": self.llm_state,
                "llmPercent": self.llm_percent,
                "llmActive": self.llm_ok,
                "models": models,
            }

    def _status(self) -> str:
        return "loading" if self.state == "loading" else "unavailable"

    def _set(self, state: str, message: str) -> None:
        with self._lock:
            self.state, self.message = state, message

    def _load_ml(self) -> None:
        if not settings.ai_enabled:
            self._set("heuristic", "Models are turned off (AI_ENABLED=false). Agents use rules only.")
            self.settled.set()
            return
        try:
            engine.load()
            self._set("ready", "Language models loaded")
        except Exception as exc:  # noqa: BLE001
            log.exception("Model loading failed")
            if engine.embed_ok:
                self._set("ready", f"Embeddings loaded; NLI unavailable ({exc}).")
            else:
                self._set("heuristic", f"Language models unavailable ({exc}). Agents use rules only.")
        finally:
            self.settled.set()

    # ---- optional LLM ---------------------------------------------------------
    def _connect_llm(self) -> None:
        client = httpx.Client(base_url=settings.ollama_url, timeout=httpx.Timeout(20.0, read=None))
        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                if client.get("/api/version").status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(3)
        else:
            self.llm_state = "unavailable"
            return
        try:
            names = {m.get("name", "") for m in client.get("/api/tags").json().get("models", [])}
            wanted = settings.llm_model if ":" in settings.llm_model else f"{settings.llm_model}:latest"
            if wanted not in names:
                self.llm_state = "downloading"
                with client.stream("POST", "/api/pull", json={"model": settings.llm_model, "stream": True}) as resp:
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        if data.get("error"):
                            raise RuntimeError(data["error"])
                        if data.get("total") and data.get("completed"):
                            self.llm_percent = int(data["completed"] * 100 / data["total"])
            client.post("/api/generate", json={"model": settings.llm_model, "prompt": "OK", "stream": False,
                                               "keep_alive": "24h", "options": {"num_predict": 2}},
                        timeout=settings.llm_timeout * 2)
            self.llm_ok = True
            self.llm_state = "ready"
        except Exception as exc:  # noqa: BLE001
            log.warning("Optional LLM not available: %s", exc)
            self.llm_state = "unavailable"


model_manager = ModelManager()
