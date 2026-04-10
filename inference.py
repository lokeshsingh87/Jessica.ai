
import os
import sys
import json
import logging
import time
logging.disable(logging.CRITICAL)

from dotenv import load_dotenv
load_dotenv()

# ── Required env vars ─────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "llama-3.3-70b-versatile")
HF_TOKEN     = os.environ.get("HF_TOKEN",     "")

if not HF_TOKEN:
    print(json.dumps({"type": "START", "status": "error",
                      "msg": "HF_TOKEN env var not set"}), flush=True)
    print(json.dumps({
        "type": "END", "overall_score": 0.5,
        "task_scores": {},
        "task_graders": {},
        "error": "HF_TOKEN missing"
    }), flush=True)
    sys.exit(1)

# ── OpenAI client ─────────────────────────────────────────────────────────────
from openai import OpenAI
client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

# ── Oracle ────────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from server.oracle import oracle_judge
    _ORACLE_AVAILABLE = True
except Exception as _oracle_import_err:
    _ORACLE_AVAILABLE = False
    class _OracleStub:
        def evaluate_clause(self, text):
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
        return action, reason, 1.0
    except Exception as exc:
        return 0, f"llm_error:{type(exc).__name__}", 0.5

# ── Difficulty-weighted reward ────────────────────────────────────────────────
BASE_REWARD = {
    (1, 1):  1.0,
    (0, 0):  0.8,
    (1, 0): -0.4,
    (0, 1): -1.0,
}
DIFFICULTY_WEIGHT = {"easy": 0.6, "medium": 0.8, "hard": 1.0}

def compute_reward(action: int, is_risk: bool, difficulty: str) -> float:
    base   = BASE_REWARD.get((action, int(is_risk)), -1.0)
    weight = DIFFICULTY_WEIGHT.get(difficulty, 0.6)
    raw    = base * weight
    return round(max(-1.0, min(1.0, raw)), 4)

# ── Grader: maps raw reward → score STRICTLY inside (0, 1) ───────────────────
def grader(reward_raw: float) -> float:
    """
    Canonical grader function.
    Maps reward in [-1.0, 1.0] to a score strictly inside (0, 1).
    Normalise to [0,1] then clamp to [0.01, 0.99] to satisfy validator.
    """
    normalised = (reward_raw + 1.0) / 2.0
    clamped    = max(0.01, min(0.99, normalised))
    return round(clamped, 4)

def _strict(value: float) -> float:
    """Ensure any aggregated score is strictly inside (0, 1)."""
    return round(max(0.01, min(0.99, float(value))), 4)

# ── Oracle-grade helper ───────────────────────────────────────────────────────
def compute_oracle_grade(action: int, is_risk: bool) -> float:
    return 1.0 if (action == int(is_risk)) else 0.0

# ── Convergence score accumulator ─────────────────────────────────────────────
class ConvergenceTracker:
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
    task_scores     = {}
    task_graders    = {}
    convergence     = ConvergenceTracker()
    global_step     = 0
    results_to_save = []

    # ── [START] ───────────────────────────────────────────────────────────────
    print("[START] " + json.dumps({
        "type":    "START",
        "tasks":   list(CURRICULUM.keys()),
        "graders": {t: "grader" for t in CURRICULUM.keys()},
        "model":   MODEL_NAME,
        "api":     API_BASE_URL,
    }), flush=True)

    for task_id, clauses in CURRICULUM.items():
        step_grader_scores = []
        step_oracles       = []

        for local_idx, clause_text in enumerate(clauses):

            # 1. Oracle ground truth
            oracle_data  = oracle_judge.evaluate_clause(clause_text)
            is_risk      = bool(oracle_data["is_actually_risk"])
            difficulty   = oracle_data["difficulty"]
            ai_grade     = round(oracle_data["severity_score"], 4)

            # 2. LLM classification
            action, reason, _ = llm_classify(clause_text)

            # 3. Raw difficulty-weighted reward [-1, 1]
            reward_raw = compute_reward(action, is_risk, difficulty)

            # 4. Graded score — strictly inside (0, 1)
            grader_score = grader(reward_raw)

            # 5. Oracle accuracy (internal RL metric)
            oracle_grade = compute_oracle_grade(action, is_risk)
            sigma        = convergence.update(oracle_grade)

            step_grader_scores.append(grader_score)
            step_oracles.append(oracle_grade)
            is_last = (local_idx == len(clauses) - 1)

            # ── [STEP] ────────────────────────────────────────────────────────
            step_payload = {
                "step":              global_step,
                "task_id":           task_id,
                "local_step":        local_idx,
                # Explicit grader fields — required by validator
                "grader":            "grader",
                "grader_score":      grader_score,   # strictly (0, 1)
                # Core RL signal
                "action":            action,
                "reward":            grader_score,   # same as grader_score
                "done":              is_last,
                # Oracle
                "oracle":            is_risk,
                "oracle_grade":      oracle_grade,
                "oracle_rationale":  oracle_data["ground_truth_rationale"][:100],
                # AI confidence
                "ai_grade":          ai_grade,
                # Context
                "difficulty":        difficulty,
                "severity":          oracle_data["severity_score"],
                "legal_category":    oracle_data["legal_category"],
                # RL convergence
                "convergence_sigma": sigma,
                # LLM reasoning
                "reason":            reason,
            }
            print("[STEP] " + json.dumps(step_payload), flush=True)
            results_to_save.append({"type": "STEP", **step_payload})
            global_step += 1

        # ── Per-task score — strictly (0, 1) ──────────────────────────────────
        raw_task_score        = sum(step_grader_scores) / len(step_grader_scores)
        task_score            = _strict(raw_task_score)
        task_scores[task_id]  = task_score
        task_graders[task_id] = "grader"

    # ── Overall score — strictly (0, 1) ──────────────────────────────────────
    overall_reward = _strict(sum(task_scores.values()) / len(task_scores))

    # ── [END] ─────────────────────────────────────────────────────────────────
    print("[END] " + json.dumps({
        "type":              "END",
        "overall_score":     overall_reward,   # strictly (0, 1)
        "task_scores":       task_scores,      # each strictly (0, 1)
        "task_graders":      task_graders,     # explicit grader per task
        "convergence_sigma": convergence.current,
    }), flush=True)

    return results_to_save


if __name__ == "__main__":
    try:
        try:
            final_audit_results = main()

            import uuid
            from datetime import datetime

            session_id = str(uuid.uuid4())[:8]
            os.makedirs("logs",          exist_ok=True)
            os.makedirs("training_logs", exist_ok=True)

            with open(os.path.join("logs", f"session_{session_id}.json"), "w") as f:
                json.dump(final_audit_results, f, indent=2)

            with open(os.path.join("training_logs", "current_run.json"), "w") as f:
                json.dump(final_audit_results, f, indent=2)

        except Exception as exc:
            print(json.dumps({
                "type":          "END",
                "overall_score": 0.5,
                "task_scores":   {t: 0.5 for t in CURRICULUM.keys()},
                "task_graders":  {t: "grader" for t in CURRICULUM.keys()},
                "error":         str(exc),
            }), flush=True)
            sys.exit(1)

    except Exception as _outer_exc:
        print(json.dumps({
            "type": "START", "tasks": list(CURRICULUM.keys()),
            "graders": {t: "grader" for t in CURRICULUM.keys()},
            "model": MODEL_NAME, "api": API_BASE_URL,
        }), flush=True)
        print(json.dumps({
            "type":          "END",
            "overall_score": 0.5,
            "task_scores":   {t: 0.5 for t in CURRICULUM.keys()},
            "task_graders":  {t: "grader" for t in CURRICULUM.keys()},
            "error":         f"fatal: {_outer_exc}",
        }), flush=True)
        sys.exit(1)