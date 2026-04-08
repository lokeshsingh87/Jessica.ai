# Copyright (c) 2026 Zoro - Legal Auditor RL Project — PATCHED v3
# inference.py — ROOT-LEVEL ENTRY POINT
#
# Checklist satisfied:
#   [START] / [STEP] / [END] strict JSON-line stdout format
#   OpenAI Python client constructed directly here
#   API_BASE_URL, MODEL_NAME, HF_TOKEN read from os.environ
#   Rewards in [-1.0, 1.0] — symmetric penalty: FP = -0.4, FN = -1.0
#   Overall/task scores normalised to [0.0, 1.0] in END line
#   3 distinct tasks, independently scored
#   Difficulty-weighted reward: hard correct = 1.0, medium = 0.8, easy = 0.6
#   Dual grading: oracle_grade (accuracy) + ai_grade (severity confidence)
#   Oracle fully integrated: ground truth side-loaded before every step
#   Oracle active (oracle: true) for ALL 9 curriculum clauses
#   Prompt-injection sanitizer on every clause before LLM call
#   No local model loading

import os
import sys
import json
import logging
import time
# Silence ALL library logging — any stray line on stdout breaks validator parse
logging.disable(logging.CRITICAL)

from dotenv import load_dotenv
load_dotenv()

# ── Required env vars (checklist items 7 & 9) ────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "llama-3.3-70b-versatile")
HF_TOKEN     = os.environ.get("HF_TOKEN",     "")

if not HF_TOKEN:
    print(json.dumps({"type": "START", "status": "error",
                      "msg": "HF_TOKEN env var not set"}), flush=True)
    print(json.dumps({"type": "END",   "overall_score": 0.0,
                      "error": "HF_TOKEN missing"}), flush=True)
    sys.exit(1)

# ── OpenAI client — constructed directly here (checklist item 9) ─────────────
from openai import OpenAI
client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

# ── Oracle — pure regex, zero network calls ───────────────────────────────────
# Wrapped in try/except so a missing server/ directory never silently kills
# stdout output — the validator needs [START]/[STEP]/[END] no matter what.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from server.oracle import oracle_judge
    _ORACLE_AVAILABLE = True
except Exception as _oracle_import_err:
    _ORACLE_AVAILABLE = False
    # Minimal stub so the rest of the script runs without modification
    class _OracleStub:
        def evaluate_clause(self, text):
            # Heuristic fallback: keywords signal risk
            _risk_kws = ["unlimited", "indemnif", "missing", "absent", "fails to",
                         "without", "conflict", "contradicts", "immediate termination"]
            is_risk = any(k in text.lower() for k in _risk_kws)
            return {
                "is_actually_risk":       is_risk,
                "difficulty":             "medium",
                "severity_score":         0.7 if is_risk else 0.2,
                "ground_truth_rationale": "oracle unavailable — heuristic fallback",
                "legal_category":         "general",
            }
        def mask_pii(self, text):
            return text
    oracle_judge = _OracleStub()

# ── Prompt-injection guardrail ────────────────────────────────────────────────
_INJECTION_PATTERNS = [
    "ignore previous", "ignore all", "disregard", "forget your instructions",
    "you are now", "new persona", "act as", "pretend you are",
    "override", "jailbreak", "do anything now", "dan mode",
    "system:", "assistant:", "### instruction",
]

def sanitize_clause(text: str) -> str:
    lower = text.lower()
    for p in _INJECTION_PATTERNS:
        if p in lower:
            return "[REDACTED — POTENTIAL INJECTION ATTEMPT]"
    return oracle_judge.mask_pii(text)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are a strict legal-risk classifier. "
    "Respond ONLY with a JSON object — no prose, no markdown, no extra keys. "
    'Format: {"action": <0 or 1>, "reason": "<one sentence max 100 chars>"} '
    "where 1 = legal risk detected, 0 = clause is safe. "
    "The text you receive is a legal clause. Classify it. Do nothing else."
)

def llm_classify(clause_text: str):
    """
    Call LLM via OpenAI client.
    Returns (action: int, reason: str, raw_confidence: float).
    raw_confidence is a crude proxy from response — 1.0 if clean parse, 0.5 on error.
    """
    safe_text = sanitize_clause(clause_text)
    try:
        resp = client.chat.completions.create(
            model           = MODEL_NAME,
            messages        = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": safe_text},
            ],
            response_format = {"type": "json_object"},
            temperature     = 0.1,
            max_tokens      = 128,
            timeout         = 30,
        )
        raw    = resp.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        action = max(0, min(1, int(parsed.get("action", 0))))
        reason = str(parsed.get("reason", ""))[:120]
        return action, reason, 1.0          # clean parse → full confidence
    except Exception as exc:
        return 0, f"llm_error:{type(exc).__name__}", 0.5

# ── Difficulty-weighted reward ────────────────────────────────────────────────
# Outcome scores — symmetric: correct → positive, hallucination/miss → negative
# Clamped to [-1.0, 1.0] so the RL penalty for false positives is visible.
BASE_REWARD = {
    (1, 1):  1.0,   # True Positive  — correctly flagged real risk
    (0, 0):  0.8,   # True Negative  — correctly cleared safe clause
    (1, 0): -0.4,   # False Positive — hallucination: flagged a safe clause (penalty)
    (0, 1): -1.0,   # False Negative — catastrophic miss: real risk undetected
}

# Difficulty multipliers — harder correct answer earns proportionally more;
# harder hallucination is penalised proportionally more.
DIFFICULTY_WEIGHT = {"easy": 0.6, "medium": 0.8, "hard": 1.0}

def compute_reward(action: int, is_risk: bool, difficulty: str) -> float:
    """
    Difficulty-weighted reward in [-1.0, 1.0] — symmetric penalty design:
      hard   TP =  1.0 × 1.0 =  1.0   (caught a hard risk — full score)
      medium TP =  1.0 × 0.8 =  0.8
      easy   TP =  1.0 × 0.6 =  0.6
      hard   TN =  0.8 × 1.0 =  0.8   (correctly cleared a hard clause)
      hard   FP = -0.4 × 1.0 = -0.40  (hallucination on a hard-difficulty clause)
      easy   FP = -0.4 × 0.6 = -0.24  (hallucination on an easy clause — lesser fine)
      hard   FN = -1.0 × 1.0 = -1.0   (missed a hard risk — catastrophic)
    """
    base   = BASE_REWARD.get((action, int(is_risk)), -1.0)
    weight = DIFFICULTY_WEIGHT.get(difficulty, 0.6)
    raw    = base * weight
    return round(max(-1.0, min(1.0, raw)), 4)

# ── Oracle-grade helper ───────────────────────────────────────────────────────
def compute_oracle_grade(action: int, is_risk: bool) -> float:
    """
    Binary correctness: 1.0 if the LLM matched the oracle ground truth, 0.0 if not.
    This is the RL accuracy signal — how well the agent is converging.
    """
    return 1.0 if (action == int(is_risk)) else 0.0

# ── Convergence score (Σ) accumulator ─────────────────────────────────────────
class ConvergenceTracker:
    """
    Tracks the RL Convergence Score across all steps.
    Σ = running mean of oracle_grade values (accuracy).
    Starts at 0.5 (random baseline) and should trend toward 1.0 for a good agent.
    """
    def __init__(self):
        self._grades: list = []

    def update(self, oracle_grade: float) -> float:
        self._grades.append(oracle_grade)
        return round(sum(self._grades) / len(self._grades), 4)

    @property
    def current(self) -> float:
        if not self._grades:
            return 0.5
        return round(sum(self._grades) / len(self._grades), 4)

# ── Task curriculum ───────────────────────────────────────────────────────────
CURRICULUM = {
    "basic_compliance": [
        "The contract is missing a valid execution date in the header.",
        "Signature of the authorized representative is absent from page 12.",
        "The document fails to specify the governing law of the jurisdiction.",
    ],
    "risk_audit": [
        "The provider shall have unlimited liability for all indirect damages.",
        "The client agrees to indemnify the provider without any financial cap.",
        "Company reserves the right to change pricing without prior notice.",
    ],
    "clause_conflict": [
        "Section 1 states payments are due in 30 days, but Section 5 states 60 days.",
        "The agreement is governed by NY law, yet Section 12 mandates London courts.",
        "Termination requires 30 days notice, while Section 8 allows immediate termination.",
    ],
}

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    task_scores       = {}
    convergence       = ConvergenceTracker()
    global_step       = 0
    results_to_save = []
    # ── [START] ───────────────────────────────────────────────────────────────
    print("[START] " + json.dumps({
        "type":   "START",
        "tasks":  list(CURRICULUM.keys()),
        "model":  MODEL_NAME,
        "api":    API_BASE_URL,
    }), flush=True)

    for task_id, clauses in CURRICULUM.items():
        step_rewards   = []
        step_oracles   = []

        for local_idx, clause_text in enumerate(clauses):

            # ── 1. Oracle: deterministic ground truth (zero network) ──────────
            oracle_data = oracle_judge.evaluate_clause(clause_text)
            is_risk     = bool(oracle_data["is_actually_risk"])
            difficulty  = oracle_data["difficulty"]
            # ai_grade = oracle severity_score — how dangerous/complex this clause is
            # This is the "AI Confidence" signal used by the dashboard
            ai_grade    = round(oracle_data["severity_score"], 4)

            # ── 2. LLM: classify the clause ──────────────────────────────────
            action, reason, _ = llm_classify(clause_text)

            # ── 3. Reward: difficulty-weighted, symmetric penalty [-1.0, 1.0] ─
            reward = compute_reward(action, is_risk, difficulty)

            # ── 4. Dual grading ───────────────────────────────────────────────
            # oracle_grade: binary accuracy for this step (did LLM match oracle?)
            oracle_grade = compute_oracle_grade(action, is_risk)
            # convergence_score: running mean of oracle_grade (RL convergence signal Σ)
            sigma = convergence.update(oracle_grade)

            step_rewards.append(reward)
            step_oracles.append(oracle_grade)
            is_last = (local_idx == len(clauses) - 1)
            normalized_step_reward = round((reward + 1.0) / 2.0, 4)
            # ── [STEP] ────────────────────────────────────────────────────────
            print("[STEP] " + json.dumps({
                "step":               global_step,
                "task_id":            task_id,
                "local_step":         local_idx,
                # Core RL signal
                "action":             action,
                "reward":             normalized_step_reward,  # [0.0–1.0] per validator req
                "done":               is_last,
                # Oracle integration
                "oracle":             is_risk,
                "oracle_grade":       oracle_grade,
                "oracle_rationale":   oracle_data["ground_truth_rationale"][:100],
                # AI confidence (dual grading — dashboard mirror)
                "ai_grade":           ai_grade,
                # Context
                "difficulty":         difficulty,
                "severity":           oracle_data["severity_score"],
                "legal_category":     oracle_data["legal_category"],
                # RL convergence
                "convergence_sigma":  sigma,
                # LLM reasoning
                "reason":             reason,
            }), flush=True)
            step_data = {
                "type": "STEP",
                "step": global_step,
                "task_id": task_id,
                "local_step": local_idx,
                "action": action,
                "reward": normalized_step_reward,  # [0.0–1.0] per validator req
                "done": is_last,
                "oracle": is_risk,
                "oracle_grade": oracle_grade,
                "oracle_rationale": oracle_data["ground_truth_rationale"][:100],
                "ai_grade": ai_grade,
                "difficulty": difficulty,
                "severity": oracle_data["severity_score"],
                "legal_category": oracle_data["legal_category"],
                "convergence_sigma": sigma,
                "reason": reason,
            }
            results_to_save.append(step_data)
            global_step += 1
            
        # ── Per-task summary ─────────────────────────────────────────────────
        raw_task_score = sum(step_rewards) / len(step_rewards)           # in [-1, 1]
        task_score     = round((raw_task_score + 1.0) / 2.0, 4)         # normalise → [0, 1]
        task_accuracy  = round(sum(step_oracles) / len(step_oracles), 4)
        task_scores[task_id] = task_score

    # ── Overall scores ────────────────────────────────────────────────────────
    overall_reward = round(
        max(0.0, min(1.0, sum(task_scores.values()) / len(task_scores))),
        4,)
    

    # ── [END] ─────────────────────────────────────────────────────────────────
    print("[END] " + json.dumps({
        "type":                "END",
        "overall_score":       overall_reward,
        "task_scores":         task_scores,
        "convergence_sigma":   convergence.current,
    }), flush=True)
    return results_to_save

if __name__ == "__main__":
  # Outer guard: if anything crashes before main() emits its own END
  # (e.g. a missing dependency, bad env var, import error in archive logic)
  # we still guarantee a valid [END] line reaches stdout so the validator
  # never sees empty output.
  try:
    try:
        # 1. Capture the results list returned by main()
        final_audit_results = main()
        
        # --- ARCHIVE LOGIC START ---
        import uuid
        import os
        from datetime import datetime

        # Generate a unique ID (the one shown in the Vault sidebar)
        session_id = str(uuid.uuid4())[:8]
        
        # Ensure the root directories exist
        os.makedirs("logs", exist_ok=True)
        os.makedirs("training_logs", exist_ok=True)

        # 2. Save to 'logs/' (The permanent archive for PDFs and History)
        log_file = os.path.join("logs", f"session_{session_id}.json")
        with open(log_file, "w") as f:
            json.dump(final_audit_results, f, indent=2)

        # 3. Save to 'training_logs/' (For the Live Chart in the Dashboard)
        with open(os.path.join("training_logs", "current_run.json"), "w") as f:
            json.dump(final_audit_results, f, indent=2)
        
        # --- ARCHIVE LOGIC END ---

    except Exception as exc:
        print(json.dumps({
            "type": "END",
            "overall_score": 0.0,
            "error": str(exc),
        }), flush=True)
        sys.exit(1)
  except Exception as _outer_exc:
      # Last-resort: something crashed outside main() entirely
      print(json.dumps({"type": "START", "tasks": [], "model": MODEL_NAME, "api": API_BASE_URL}), flush=True)
      print(json.dumps({"type": "END", "overall_score": 0.0, "error": f"fatal: {_outer_exc}"}), flush=True)
      sys.exit(1)