---
title: Jessica.ai - Legal Auditor
emoji: ⚖️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# ⚖️ Jessica.ai: AI-Powered Legal Auditor

**Jessica.ai** is a high-performance legal contract analysis platform built for the **Meta AI Hackathon (by Scaler)**. It leverages **OpenEnv** and **Groq (Meta Llama 3)** to provide real-time risk assessment, clause grading, and automated PDF report generation.

---

## 🚀 Key Features
- **Intelligent Contract Parsing**: Automated text extraction from PDF and Text contracts via PyMuPDF.
- **Oracle Grading Engine**: Powered by **Meta Llama 3** for institutional-grade legal reasoning and sub-second responses.
- **OpenEnv Sandbox**: An RL-inspired simulation environment to audit legal clauses against safety and compliance standards.
- **Dynamic PDF Generation**: Generates professional, ready-to-print legal audit reports using ReportLab.
- **Developer API**: High-speed FastAPI backend for session management and JSON/PDF data export.

## 🛠️ Tech Stack & Architecture
- **AI/ML**: Meta Llama 3 (via Groq), OpenEnv Core 0.1.3
- **Backend**: FastAPI (Python 3.11)
- **PDF Engine**: ReportLab & PyMuPDF (fitz)
- **Containerization**: Docker (Optimized for Hugging Face Spaces)

---

## 📦 Docker & Local Execution

### 1. Environment Configuration
To run this project, ensure you have the following environment variables set (either in a `.env` file or as Hugging Face Secrets):

| Variable | Description |
| :--- | :--- |
| `HF_TOKEN` | Your Groq API Key (used as a placeholder for OpenEnv) |
| `GROQ_API_KEY` | Your Groq API Key (for the Oracle Engine) |
| `ADMIN_TOKEN` | Your secure password for PDF exports (e.g., `dev_secret_zoro`) |
| `ALLOWED_ORIGINS` | The URL of your frontend or HF Space |

### 2. Execution Commands
Build and run the container with these commands:

```bash
# Build the image
docker build -t jessica-ai .

# Run the container locally
docker run -p 7860:7860 \
  -e HF_TOKEN=your_key \
  -e GROQ_API_KEY=your_key \
  -e ADMIN_TOKEN=dev_secret_zoro \
  jessica-ai

Security & Access Logic
Jessica.ai implements a multi-layered security architecture:

Session Isolation: Each audit is assigned a unique UUID. Users can only access data associated with their specific x-session-token.

Admin Verification: Sensitive endpoints (like /developer/sessions and PDF exports) are protected by a custom verify_session_access middleware.

Secret Masking: Access tokens are verified using secrets.compare_digest to prevent timing attacks.

CORS Protection: The API only accepts requests from trusted origins defined in the environment.

👤 Author
Lokesh (M0SSHEAD)
Computer Science Graduate & AI Developer
Specializing in AI Safety, Legal Tech, and Scalable Backend Systems.

Developed for the Meta AI Hackathon organized by Scaler (April 2026).