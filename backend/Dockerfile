FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

# CPU-only PyTorch (small, works on Intel/AMD and Apple Silicon, no GPU needed)
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the models into the image so the app runs offline after the build.
ARG EMBED_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
ARG NLI_MODEL=MoritzLaurer/mDeBERTa-v3-base-mnli-xnli
ENV EMBED_MODEL=${EMBED_MODEL} \
    NLI_MODEL=${NLI_MODEL}
COPY app/ml/download.py /tmp/download.py
RUN python /tmp/download.py && rm /tmp/download.py

ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
