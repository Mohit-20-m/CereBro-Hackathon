"""Local transformer models.

* Sentence embeddings (paraphrase-multilingual-MiniLM-L12-v2): meaning of a
  message as a vector, for similarity, repeat detection, intent prototypes and
  topic phrases. Milliseconds per message on CPU.
* NLI (mDeBERTa-v3-base-mnli-xnli): zero-shot classification by entailment,
  used to judge whether a reply answers a question, and for intent when the
  embedding comparison is not confident.

If the models cannot be loaded, `ready` stays False and agents fall back to
their lightweight rules, so the app keeps working.
"""
from __future__ import annotations

import logging
import os
import threading

from ..config import settings

log = logging.getLogger("anvaya.ml")


class Engine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.embedder = None
        self.nli_tokenizer = None
        self.nli_model = None
        self.entail_idx = 0
        self.embed_ok = False
        self.nli_ok = False

    @property
    def ready(self) -> bool:
        return self.embed_ok

    def load(self) -> None:
        import torch

        threads = settings.ml_threads or max(1, min(4, os.cpu_count() or 1))
        torch.set_num_threads(threads)
        from sentence_transformers import SentenceTransformer

        log.info("Loading embedding model %s", settings.embed_model)
        self.embedder = SentenceTransformer(settings.embed_model, device="cpu")
        self.embedder.encode(["warm up"], show_progress_bar=False)
        self.embed_ok = True

        if settings.nli_enabled:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            log.info("Loading NLI model %s", settings.nli_model)
            self.nli_tokenizer = AutoTokenizer.from_pretrained(settings.nli_model)
            self.nli_model = AutoModelForSequenceClassification.from_pretrained(settings.nli_model).eval()
            label2id = {k.lower(): v for k, v in self.nli_model.config.label2id.items()}
            self.entail_idx = next(v for k, v in label2id.items() if k.startswith("entail"))
            self.classify("warm up", ["a test"], "This is {}.")
            self.nli_ok = True

    def embed(self, texts: list[str]) -> list[list[float]]:
        with self._lock:
            vectors = self.embedder.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
        return [[round(float(x), 5) for x in v] for v in vectors]

    def classify(self, premise: str, labels: list[str], template: str) -> dict[str, float]:
        """Zero-shot: probability (softmax across labels) that `premise` entails each label."""
        import torch

        hypotheses = [template.format(label) for label in labels]
        with self._lock, torch.no_grad():
            enc = self.nli_tokenizer(
                [premise] * len(hypotheses), hypotheses, return_tensors="pt",
                padding=True, truncation=True, max_length=256,
            )
            logits = self.nli_model(**enc).logits[:, self.entail_idx]
            probs = torch.softmax(logits, dim=0).tolist()
        return dict(zip(labels, probs))


engine = Engine()
