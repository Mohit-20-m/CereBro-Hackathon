# ANVAYA

**Connecting context. Detecting gaps.**

ANVAYA analyzes group conversations, including code-mixed Kanglish, Hinglish and Manglish, and finds communication gaps: unanswered questions, ignored requests, repeated requests, clarification loops and unresolved topics. For every gap it shows *why* it was flagged and the exact messages that prove it.

A team of LangGraph agents does the work, powered by small local transformer models that run on any laptop CPU. The models extract meaning; a transparent scoring step decides whether communication actually broke down, so every flag can be explained.

## Run it

You need Docker Desktop (or Docker Engine with Compose v2). Same command on Windows, Mac and Linux:

```bash
docker compose up --build
```

Then open **http://localhost:5173**.

The first build takes a few minutes: it installs CPU-only PyTorch and downloads two small transformer models (about 1.5 GB) **into the image**. After that the app runs fully offline, needs no GPU and no Ollama, and starts in seconds. Give Docker at least 3 GB of memory (Docker Desktop → Settings → Resources).

To stop: `Ctrl+C` or `docker compose down`. To wipe the database too: `docker compose down -v`.

## What you can do

- **Open a sample group** (Hackathon Team 5, Office Chats, Friends Forever) and see its gaps in the insights panel.
- **View evidence** on any gap: the reasons, the exact messages with their roles, a timeline, the score breakdown, and whether the Critic agent confirmed it.
- **Replay conversation** to watch messages arrive one by one and gaps appear at the moment the agents detected them.
- **Type as any member** using the picker next to the message box. Every new message is analyzed by the agents and the gaps update live.
- **New group** to start a fresh conversation with your own members.
- **Import chat** to analyze a `.txt` file: WhatsApp exports (Android or iOS), `Name: message` lines, or the ANVAYA format below.
- **Dashboard** shows statistics, topics, the scoring rules and the **Agent activity** log of the latest LangGraph run.

Nothing in the UI is hard-coded: the sample chats are ordinary text files in `data/`, loaded into PostgreSQL on first start and analyzed like any other chat. Add your own `.txt` files there before the first start, or import them from the UI at any time.

### Chat file format

```
# name: Hackathon Team 5
# members: Aishu, Rahul, Keerti, Mohit

[Aishu] [10:21]
Guys schema yaaru send madidru?
[Rahul] [10:22]
Frontend almost done.
```

## Models

| Purpose | Model | Size | Speed on a laptop CPU |
|---|---|---|---|
| Meaning, similarity, intent examples, topic phrases | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | ~470 MB | milliseconds per message |
| Does this reply answer the question? Unclear intents | `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` (zero-shot NLI) | ~1.1 GB | ~0.1–0.3 s per check |
| Optional reasoning for Investigator and Critic | `qwen2.5:1.5b` via Ollama | ~1 GB | off by default |

Romanized chat (Kanglish, Hinglish, Manglish) is normalized before embedding: common words such as *yaaru → who*, *kisi → anyone*, *madthini → I will* are mapped to English, so "schema yaaru send madidru?" is read as "schema who did send?". The original text is always what you see; click the language chip on a message to see how the agents read it.

## How the agents work

```
START → Language → Intent → Topic → Response Matcher ⇄ Investigator
                                          ↓
                                    Gap Detector → Critic (loops per gap) → Evidence Generator → END
```

| Agent | What it does |
|---|---|
| Language Analyzer | Detects script, languages and code-mixing; normalizes romanized text; embeds every message with MiniLM. |
| Intent Analyzer | Compares each message's embedding with example phrases for each intent. If not confident, asks the NLI model zero-shot. |
| Topic Analyzer | Embedding-based keyphrase extraction: picks the phrase closest in meaning to the message and merges it into existing topics by similarity. Short replies inherit the topic they answer. |
| Response Matcher (agentic) | Attaches repeats and re-asks to the original thread; checks the next replies, using similarity to choose which are worth judging and the NLI model to judge *answers / postpones / unrelated*. Hands unsure cases to the Investigator. |
| Investigator (agentic) | A tool loop, one tool per LangGraph step: `find_similar`, `search_messages`, `get_messages_by_speaker`, `get_messages_after`. It chooses the next tool from what earlier tools found (or the optional LLM chooses, ReAct style). Every answer it proposes is verified by the NLI judge. |
| Gap Detector | Never asks a model "is there a gap?". It replays the conversation message by message and scores each thread with fixed weights. |
| Critic (agentic) | Challenges every open gap by independently judging related replies the matcher skipped (or re-reading with the optional LLM). A gap is only marked resolved if the NLI judge agrees. |
| Evidence Generator | Evidence list, plain-language reasons, confidence, a one-line summary, topic status over time. |

### Scoring

| Signal | Weight |
|---|---|
| Unanswered question | 0.40 |
| Repeated request | 0.25 |
| Topic recurrence | 0.20 |
| Clarification | 0.15 |

0.00 to 0.30 is normal, 0.30 to 0.60 a possible gap, 0.60 to 1.00 a strong gap.

**Confidence** = 45 + 45 × score + 2 per unanswered reply (up to 5), plus 4 when the Critic confirmed the gap, minus 10 in heuristic mode, limited to 30–97%.

### Speed and caching

Every agent decision is cached in the database, so a new message only triggers new work. On a normal laptop the sample chats are analyzed within seconds, and a new message in about a second.

### Optional LLM

The app does not need an LLM. If you want the Investigator and Critic to reason in words, connect a small one through Ollama:

- **Ollama app installed (Mac, Windows, Linux):** add `OLLAMA_URL=http://host.docker.internal:11434` to `.env`.
- **Ollama in Docker:** add `OLLAMA_URL=http://ollama:11434` to `.env` and run `docker compose --profile llm up --build`.

The model (`qwen2.5:1.5b`) is pulled automatically. If the LLM is slow or unreachable, the agents simply carry on without it.

### Rule-based mode

If the models can't load, every agent falls back to built-in rules and the app keeps working with a notice at the top. Set `AI_ENABLED=false` to use this mode on purpose.

## Configuration

Copy `.env.example` to `.env` to change settings.

| Variable | Default | Notes |
|---|---|---|
| `AI_ENABLED` | `true` | `false` = rules only, no models. |
| `NLI_ENABLED` | `true` | `false` skips mDeBERTa (saves ~1 GB RAM, less accurate). |
| `OLLAMA_URL` | empty | Optional LLM, see above. |
| `LLM_MODEL` | `qwen2.5:1.5b` | Only used when `OLLAMA_URL` is set. |
| `FRONTEND_PORT` | `5173` | |
| `BACKEND_PORT` | `8000` | API docs at http://localhost:8000/docs |

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Database and AI model status |
| GET | `/api/meta` | Gap types, signal weights, agent list |
| GET | `/api/conversations` | All conversations with open gap counts |
| POST | `/api/conversations` | Create a group `{name, members}` |
| POST | `/api/conversations/import` | Upload a `.txt` chat (multipart `file`, optional `name`) |
| GET | `/api/conversations/{id}` | Messages, gaps with stages and evidence, topics, insights, agent trace |
| POST | `/api/conversations/{id}/messages` | Send `{sender, text, time?}`; analysis runs automatically |
| POST | `/api/conversations/{id}/members` | Add a member `{name}` |
| POST | `/api/conversations/{id}/analyze` | Run the agents again |
| GET | `/api/conversations/{id}/gaps` · `/topics` · `/insights` | Parts of the analysis |
| DELETE | `/api/conversations/{id}` | Delete a conversation |

## Project structure

```
anvaya/
├── docker-compose.yml         # db + ollama + backend + frontend
├── .env.example
├── data/                      # sample chats loaded on first start
├── backend/
│   ├── Dockerfile
│   └── app/
│       ├── main.py            # startup: DB, seeding, model setup, worker
│       ├── api/routes.py
│       ├── agents/            # LangGraph graph and the agents
│       ├── ml/                # transformer models, romanized normalizer, intent examples
│       ├── ai/                # model manager, lexicon, optional LLM client
│       ├── database/          # models, connection, seed
│       └── services/          # chat parsing, analysis worker
└── frontend/
    ├── Dockerfile             # builds the app, serves it with nginx
    ├── nginx.conf             # proxies /api to the backend
    └── src/
```

## Local development without Docker

Backend (uses SQLite unless `DATABASE_URL` is set; models download on first run):

```bash
cd backend
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
DATA_DIR=../data uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Troubleshooting

- **The build fails while downloading models:** the first build needs internet access to huggingface.co and download.pytorch.org. Run `docker compose build --no-cache backend` to retry.
- **"Language models unavailable" banner:** check `docker compose logs backend`. The app still works in rule-based mode meanwhile.
- **Backend restarts or is killed:** Docker needs more memory. Give it at least 3 GB, or set `NLI_ENABLED=false`.
- **Port already in use:** change `FRONTEND_PORT` or `BACKEND_PORT` in `.env`.
