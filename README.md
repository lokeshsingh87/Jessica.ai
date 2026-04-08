⚖️ Legal Auditor AI Environment
An automated legal contract auditing environment built for the Meta OpenEnv Hackathon. This project leverages Reinforcement Learning patterns to train and evaluate AI agents on their ability to detect high-risk clauses in professional contracts.

🌟 Overview
Unlike a simple text-processing script, this environment uses the LexGLUE/LEDGAR dataset—a collection of 60,000+ labeled legal clauses—to provide a realistic "Gym" for AI auditors.

The environment presents a legal clause, and the Agent must decide whether to Flag (1) it as a risk or mark it as Safe (0).

🚀 Quick Start
1. Prerequisites
Docker Desktop (WSL2 Integration enabled)

Python 3.10+

Hugging Face Token (Read Access)

2. Environment Variables
You must export these variables in your terminal so the inference.py and the server can communicate with the LLM router:
export HF_TOKEN="your_huggingface_read_token"
export MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"
export API_BASE_URL="https://router.huggingface.co/v1"
3. Running with Docker (Recommended)
This is the "Submission-Ready" way to run the project:
# Build the image
docker build -t legal_auditor .

# Start the environment server
docker run -p 8000:8000 -e HF_TOKEN=$HF_TOKEN legal_auditor
4. Running the Auditor (Inference)
In a separate terminal window, execute the agent logic:
export PYTHONPATH=$PYTHONPATH:.
uv run python inference.py
