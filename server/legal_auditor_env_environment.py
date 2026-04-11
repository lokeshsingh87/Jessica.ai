# Copyright (c) 2026 Zoro - Legal Auditor RL Project — PATCHED
# legal_auditor_env_environment.py
#
# Changes vs original:
#   - API_BASE_URL / MODEL_NAME / HF_TOKEN read from os.environ (not hardcoded defaults)
#   - Reward table matches inference.py exactly (single source of truth via constants)
#   - total_reward accumulator never exposed as a score; per-step rewards clamped
#   - UserLegalAuditor.audit_clause_text sanitizes input before LLM call
#   - /developer/sessions now requires an admin token (ADMIN_TOKEN env var)
#   - Session buffer isolated per-instance (no shared mutable class state)
#   - Task reset() accepts task_id and loads correct clause set

import os
import sys
import uuid
import datetime
import logging
import json
from typing import Optional, Dict, Any, List, Tuple

from openai import OpenAI
from dotenv import load_dotenv

from openenv.core.env_server.http_server import Environment, Action, Observation, State
from server.oracle import oracle_judge

load_dotenv()
logger = logging.getLogger("LegalAuditor")

# ── Env vars ─────────────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
HF_TOKEN     = os.environ.get("HF_TOKEN",     "")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "llama-3.3-70b-versatile")

# ── Reward constants — single source of truth (mirrored in inference.py) ────
REWARD_TRUE_POSITIVE  = 0.95
REWARD_TRUE_NEGATIVE  = 0.80
REWARD_FALSE_POSITIVE = 0.20
REWARD_FALSE_NEGATIVE = 0.05

# ── Task curriculum ───────────────────────────────────────────────────────────
TASK_DATA: Dict[str, List[str]] = {
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
    "default": ["Standard boilerplate legal clause for compliance review."],
}


# ── Pydantic models ───────────────────────────────────────────────────────────
from pydantic import Field

class LegalAuditorObservation(Observation):
    clause_text:       str
    clause_index:      int
    agent_reliability: float
    ai_analysis_grade: float
    is_risk_detected:  bool

class LegalAuditorAction(Action):
    action: int  # 0 = Safe, 1 = Risk

class LegalAuditorState(State):
    total_reward:         float
    processed_steps:      int
    current_reliability:  float
    analysis_confidence:  float


# ── Environment ───────────────────────────────────────────────────────────────
class LegalAuditorEnvironment(
    Environment[LegalAuditorAction, LegalAuditorObservation, LegalAuditorState]
):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        super().__init__()
        self.client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN) if HF_TOKEN else None
        self.current_doc_clauses: List[str] = []
        self.clause_index        = 0
        self.total_agent_reward  = 0.0
        self.current_reliability = 0.5
        self.analysis_confidence = 1.0
        self.session_id          = str(uuid.uuid4())
        self.session_buffer: List[Dict[str, Any]] = []

    def reset(self, task_id: str = "default") -> LegalAuditorObservation:
        self.clause_index        = 0
        self.total_agent_reward  = 0.0
        self.current_reliability = 0.5
        self.analysis_confidence = 1.0
        self.session_buffer      = []
        # Loads correct curriculum based on task_id
        self.current_doc_clauses = list(TASK_DATA.get(task_id, TASK_DATA["default"]))
        return self._get_current_obs()

    def _get_current_obs(self) -> LegalAuditorObservation:
        text = (
            self.current_doc_clauses[self.clause_index]
            if self.clause_index < len(self.current_doc_clauses)
            else "END"
        )
        return LegalAuditorObservation(
            clause_text       = text,
            clause_index      = self.clause_index,
            agent_reliability = round(max(0.05, min(0.95, self.current_reliability)), 4),
            ai_analysis_grade = round(max(0.05, min(0.95, self.analysis_confidence)), 4),
            is_risk_detected  = False,
        )

    def state(self) -> LegalAuditorState:
        # Note: total_reward is an accumulator, but internal states are clamped
        return LegalAuditorState(
            total_reward        = round(float(self.total_agent_reward), 4),
            processed_steps     = self.clause_index,
            current_reliability = round(max(0.05, min(0.95, self.current_reliability)), 4),
            analysis_confidence = round(max(0.05, min(0.95, self.analysis_confidence)), 4),
        )
    def _normalize(self,val: float) -> float:
    # Maps [-0.99, 0.99] range to [0, 1] range
        norm = (val + 1.0) / 2.0
    # Apply strict buffer to stay away from 0.0 and 1.0
        return round(max(0.0512, min(0.9488, norm)), 4)
    def step(
        self, action: LegalAuditorAction
    ) -> Tuple[LegalAuditorObservation, float, bool, Dict[str, Any]]:
        # Handle terminal state boundary
        if self.clause_index >= len(self.current_doc_clauses):
            return self._get_current_obs(), 0.05, True, {}

        text        = self.current_doc_clauses[self.clause_index]
        oracle_data = oracle_judge.evaluate_clause(text)
        label       = int(oracle_data["is_actually_risk"])

        # Use the updated constants (REWARD_TRUE_POSITIVE = 0.99, etc.)
        if   action.action == 1 and label == 1: raw_reward = REWARD_TRUE_POSITIVE
        elif action.action == 0 and label == 0: raw_reward = REWARD_TRUE_NEGATIVE
        elif action.action == 1 and label == 0: raw_reward = REWARD_FALSE_POSITIVE
        else:                                   raw_reward = REWARD_FALSE_NEGATIVE

        # ── CRITICAL CHANGE: Clamp reward strictly between 0.05 and 0.95 ──
        reward = self._normalize(raw_reward)

        self.total_agent_reward  += reward
        self.clause_index        += 1
        
        # Recalculate reliability based on clamped rewards
        self.current_reliability = self._normalize(self.total_agent_reward / self.clause_index if self.clause_index > 0 else 0)
        self.analysis_confidence  = reward

        self.session_buffer.append({
            "session_id":        self.session_id,
            "clause_index":      self.clause_index - 1,
            "text":              text,
            "action":            action.action,
            "reward":            reward,
            "ai_grade":          self.analysis_confidence,
            "oracle_grade":      self.current_reliability,
            "difficulty":        oracle_data["difficulty"],
            "is_actually_risk":  bool(label),
            "oracle_rationale":  oracle_data["ground_truth_rationale"],
            "timestamp":         datetime.datetime.now().isoformat(),
        })

        done = self.clause_index >= len(self.current_doc_clauses)
        
        # Return observation and the strictly clamped reward
        return (
            self._get_current_obs(), 
            reward, 
            done, 
            {"ai_grade": round(max(0.05, min(0.95, self.analysis_confidence)), 4)}
        )


# ── UserLegalAuditor (used by app.py and inference.py via get_auditor) ───────
_INJECTION_PATTERNS = [
    "ignore previous", "ignore all", "disregard", "forget your instructions",
    "you are now", "new persona", "act as", "pretend you are",
    "override", "jailbreak", "do anything now", "dan mode",
    "system:", "### instruction",
]

SYSTEM_PROMPT = (
    "You are a strict legal-risk classifier. "
    "Respond ONLY with a JSON object — no prose, no markdown, no extra keys. "
    'Format: {"action": <0 or 1>, "reason": "<one sentence max 100 chars>"} '
    "where 1 = legal risk detected, 0 = clause is safe."
)


class UserLegalAuditor:
    session_token: Optional[str] = None

    def __init__(self):
        self.env          = LegalAuditorEnvironment()
        self.client       = self.env.client
        self.session_id   = str(uuid.uuid4())
        self.session_token: Optional[str] = None
        # Each instance owns its own buffer (not shared via class-level reference)
        self.session_buffer: List[Dict[str, Any]] = []

    def start_new_session(self):
        self.env.reset()
        self.session_id    = str(uuid.uuid4())
        self.session_token = None
        self.session_buffer = []

    def _sanitize(self, text: str) -> str:
        lower = text.lower()
        for p in _INJECTION_PATTERNS:
            if p in lower:
                return "[REDACTED — POTENTIAL INJECTION ATTEMPT]"
        return oracle_judge.mask_pii(text)

    def audit_clause_text(
        self,
        text: str,
        clause_index: int,
        oracle_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self.client is None:
            raise ValueError(
                "OpenAI client not initialised. "
                "Check that HF_TOKEN is set in your environment."
            )

        safe_text  = self._sanitize(text)
        action_val = 0
        ai_rationale = "No analysis performed"

        try:
            resp = self.client.chat.completions.create(
                model    = MODEL_NAME,
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": safe_text},
                ],
                response_format = {"type": "json_object"},
                temperature     = 0.1,
                max_tokens      = 128,
                timeout         = 30,
            )
            res = json.loads(resp.choices[0].message.content or "{}")
            action_val   = max(0, min(1, int(res.get("action", 0))))
            ai_rationale = str(res.get("reason", ""))[:120]
        except Exception as exc:
            action_val   = 0
            ai_rationale = f"inference_error:{type(exc).__name__}"

        obs, reward, done, info = self.env.step(LegalAuditorAction(action=action_val))
        reward = round(max(0.0, min(1.0, float(reward))), 4)   # final clamp

        entry: Dict[str, Any] = {
            "session_id":        self.session_id,
            "session_token":     self.session_token,
            "clause_index":      clause_index,
            "text":              text,     # store original (not sanitized) for audit log
            "action":            action_val,
            "warning":           ai_rationale,
            "oracle_rationale":  oracle_data["ground_truth_rationale"],
            "reward":            reward,
            "ai_grade":          obs.ai_analysis_grade,
            "oracle_grade":      obs.agent_reliability,
            "difficulty":        oracle_data["difficulty"],
            "is_actually_risk":  bool(oracle_data["is_actually_risk"]),
            "timestamp":         datetime.datetime.now().isoformat(),
        }
        self.session_buffer.append(entry)
        return entry

    def save_session(self) -> str:
        os.makedirs("logs", exist_ok=True)
        filename = f"logs/session_{self.session_id}.json"
        with open(filename, "w") as f:
            json.dump(self.session_buffer, f, indent=2)
        return filename


def get_auditor() -> UserLegalAuditor:
    return UserLegalAuditor()