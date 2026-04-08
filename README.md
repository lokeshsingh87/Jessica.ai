---
title: Jessica.ai - Legal Auditor
emoji: ⚖️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Jessica.ai — Legal Document Auditor

> **AI-powered legal risk intelligence. Upload your contract. Get the truth.**

Jessica.ai is a reinforcement-learning-backed legal auditing system that reads your legal documents clause by clause, flags risks, confirms safe language, and delivers a full performance report with reward graphs and oracle-graded accuracy scores — all in a sleek, real-time dashboard.

---

## What It Does

Drop in any legal document — contract, NDA, SLA, terms of service — and Jessica.ai will:

- **Flag risky clauses** — unlimited liability, missing governing law, uncapped indemnity, contradictory terms, and more
- **Confirm safe clauses** — clearly mark what's compliant and low-risk
- **Score every decision** — each clause gets a difficulty-weighted RL reward showing how confident and correct the AI was
- **Grade against Oracle truth** — a deterministic rule-based oracle independently evaluates each clause so you can see exactly where the AI agreed or diverged
- **Render convergence graphs** — watch the cumulative reward trajectory and confusion matrix build in real time
- **Export full reports** — download a PDF audit report or raw JSON for every session

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM Inference | [Groq API](https://groq.com) — `llama-3.3-70b-versatile` via OpenAI-compatible client |
| Backend | FastAPI + OpenEnv (RL environment server) |
| Frontend | React + Vite + Tailwind CSS + Recharts |
| Containerisation | Docker (`python:3.11-slim`) |
| Deployment | Hugging Face Spaces |
| RL Framework | Custom OpenEnv environment with difficulty-weighted reward shaping |
| Oracle | Deterministic regex-based ground-truth grader (zero network calls) |

---

## How the Scoring Works

Jessica.ai uses a **difficulty-weighted reinforcement learning reward** for every clause:

```
True Positive  (caught a real risk)   →  +1.0 × difficulty_weight
True Negative  (correctly cleared)    →  +0.8 × difficulty_weight
False Positive (hallucinated a risk)  →  -0.4 × difficulty_weight
False Negative (missed a real risk)   →  -1.0 × difficulty_weight
```

Difficulty weights: `easy = 0.6` · `medium = 0.8` · `hard = 1.0`

Raw rewards are normalised to `[0.0, 1.0]` for reporting. The **Oracle Consensus %** shows how often the AI matched the ground truth — a score above 80% means the agent is well-calibrated on your document type.

---

## Dashboard Features

**Analysis Tab**
- Live clause-by-clause audit cards with Agent verdict vs Oracle truth
- Risk flag count, Reliability Grade, Oracle Consensus meter
- Agent Final Inference summary
- Export to PDF report or JSON

**Performance Tab**
- Reward Convergence Trajectory chart (area graph, cumulative RL reward)
- Confusion Matrix (TP / FP / FN / TN with animated bars)
- Full Inference Trajectory Log
- Export Agent Performance Report

**Audit Vault (Sidebar)**
- Full session history — persists across page refreshes
- Session-token security layer — each audit is locked to its session token
- Unlock modal for recovering sessions by ID + token
- Search and filter past audits

---

## Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend build)
- A [Groq API key](https://console.groq.com)

### 1. Clone and set up environment

```bash
git clone https://github.com/your-username/jessica-ai.git
cd jessica-ai
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
API_BASE_URL=https://api.groq.com/openai/v1
MODEL_NAME=llama-3.3-70b-versatile
HF_TOKEN=your_groq_api_key_here
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:7860
ADMIN_TOKEN=your_admin_token_here
```

### 3. Build the frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Start the server

```bash
python server/app.py
```

Visit `http://localhost:7860`

---

## Running with Docker

### Build

```bash
docker build -t jessica-ai .
```

### Run

```bash
docker run -p 7860:7860 --env-file .env jessica-ai
```

Visit `http://localhost:7860`

---

## Running the Inference Script

The standalone inference script runs the full 3-task RL evaluation curriculum against the Groq API and emits structured logs for the validator.

```bash
python inference.py
```

Expected output format:

```json
{"type": "START", "tasks": ["basic_compliance", "risk_audit", "clause_conflict"], ...}
{"type": "STEP", "step": 0, "task_id": "basic_compliance", "action": 1, "reward": 0.9, ...}
...
{"type": "END", "overall_score": 0.87, "task_scores": {...}, "convergence_sigma": 0.89}
```

### Tasks covered

| Task | What it tests |
|---|---|
| `basic_compliance` | Missing dates, signatures, governing law |
| `risk_audit` | Unlimited liability, uncapped indemnity, unilateral pricing changes |
| `clause_conflict` | Contradictory payment terms, jurisdiction conflicts, notice period clashes |

---

## Deployment on Hugging Face Spaces

1. Create a new Space on [huggingface.co/spaces](https://huggingface.co/spaces) with **Docker** as the SDK
2. Push this repository to the Space
3. Set the following **Space Secrets** in Settings → Variables and secrets:

```
API_BASE_URL   = https://api.groq.com/openai/v1
MODEL_NAME     = llama-3.3-70b-versatile
HF_TOKEN       = your_groq_api_key
ALLOWED_ORIGINS = https://your-space-name.hf.space
ADMIN_TOKEN    = your_admin_token
```

4. The Space will build automatically. The `/reset` endpoint returns 200 for the OpenEnv health check.

---

## Project Structure

```
jessica-ai/
├── inference.py              # Standalone RL evaluation script (validator entry point)
├── models.py                 # Pydantic action/observation models
├── requirements.txt
├── Dockerfile
├── openenv.yaml              # OpenEnv spec
├── server/
│   ├── app.py                # FastAPI server — audit, export, session endpoints
│   ├── legal_auditor_env_environment.py   # OpenEnv RL environment
│   ├── oracle.py             # Deterministic ground-truth grader
│   ├── pdf_generator.py      # Oracle audit PDF export
│   └── user_report_generator.py          # User-facing PDF export
├── frontend/
│   ├── src/
│   │   └── Dashboard.jsx     # Full React dashboard
│   └── ...
├── logs/                     # Session audit logs (auto-created)
└── training_logs/            # RL training data (auto-created)
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `API_BASE_URL` | ✅ | LLM API endpoint (Groq: `https://api.groq.com/openai/v1`) |
| `MODEL_NAME` | ✅ | Model identifier (`llama-3.3-70b-versatile`) |
| `HF_TOKEN` | ✅ | Your Groq / Hugging Face API key |
| `ALLOWED_ORIGINS` | ✅ | Comma-separated CORS origins |
| `ADMIN_TOKEN` | ⚠️ | Enables `/developer/sessions` endpoint. Leave unset to disable. |
| `MAX_FILE_BYTES` | ➖ | Max upload size in bytes (default: 5MB) |
| `MAX_CLAUSES` | ➖ | Max clauses parsed per document (default: 200) |

---

## Security

- Every audit session is protected by a **session token** generated at upload time
- Tokens are stored client-side in localStorage and must be presented to access session data, stats, or exports
- The `/developer/sessions` admin endpoint is disabled unless `ADMIN_TOKEN` is explicitly set
- File size and clause count are capped server-side against DoS
- Session IDs are validated against a strict regex before any filesystem access (path traversal guard)
- All rewards are clamped to `[0.0, 1.0]` before leaving the API
- Fully validated via OpenEnv Submission Suite (3/3 checks passed).

---

## License
Lokesh Singh
MIT — built for the Meta AI Hackathon organised by Scaler.

---

<div align="center">
  <sub>Built with Groq · FastAPI · React · Docker · Hugging Face Spaces</sub>
</div>