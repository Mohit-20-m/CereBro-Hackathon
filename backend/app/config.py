"""Runtime settings, read from environment variables (see .env.example)."""
import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() not in ("0", "false", "no", "off")


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./anvaya.db")
    data_dir: str = os.getenv("DATA_DIR", "/app/data")

    # Local transformer models (downloaded into the Docker image at build time).
    embed_model: str = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    nli_model: str = os.getenv("NLI_MODEL", "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")
    nli_enabled: bool = _bool("NLI_ENABLED", True)
    ml_threads: int = _int("ML_THREADS", 0)  # 0 = choose automatically

    # AI_ENABLED=false skips the models entirely (rule-based fallback only).
    ai_enabled: bool = _bool("AI_ENABLED", True)

    # Optional small LLM through Ollama, used only by the Investigator, Critic and
    # summaries. Empty OLLAMA_URL = off. Everything works without it.
    ollama_url: str = os.getenv("OLLAMA_URL", "").rstrip("/")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5:1.5b")
    llm_timeout: float = float(os.getenv("LLM_TIMEOUT", "90"))
    llm_num_ctx: int = _int("LLM_NUM_CTX", 4096)

    # Analysis tuning
    response_window: int = _int("RESPONSE_WINDOW", 4)
    min_replies_for_gap: int = _int("MIN_REPLIES_FOR_GAP", 2)
    investigator_max_steps: int = _int("INVESTIGATOR_MAX_STEPS", 3)
    critic_context_messages: int = _int("CRITIC_CONTEXT_MESSAGES", 20)


settings = Settings()
