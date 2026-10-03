"""Downloads the transformer models into HF_HOME. Run once at Docker build time,
so the running app never needs internet access for its models."""
import os

from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

embed = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
nli = os.getenv("NLI_MODEL", "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")

print(f"Downloading {embed}")
SentenceTransformer(embed, device="cpu").encode(["warm up"])
print(f"Downloading {nli}")
AutoTokenizer.from_pretrained(nli)
AutoModelForSequenceClassification.from_pretrained(nli)
print("Models ready")
