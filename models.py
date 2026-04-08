# Copyright (c) 2026 Zoro - Legal Auditor RL Project
from openenv.core.env_server.http_server import Action, Observation
from pydantic import Field
from typing import Optional

class LegalAuditorAction(Action):
    """
    Actions the AI takes while auditing a contract.
    0 = Safe (No Risk), 1 = Risk Detected (Flag).
    """
    action: int = Field(..., ge=0, le=1, description="0 for Safe, 1 for High Risk Flag")
    rationale: Optional[str] = Field(None, description="The deductive reasoning behind the classification")

class LegalAuditorObservation(Observation):
    """
    Synchronized with LegalAuditorEnvironment.step() output.
    Includes dual-grading metrics for both accuracy and confidence.
    """
    clause_text: str = Field(..., description="The specific legal clause text currently under review")
    clause_index: int = Field(..., description="The sequential index of the current clause")
    
    # Dual-Grading Metrics (Must be in 0.0 - 1.0 range for validator)
    agent_reliability: float = Field(..., ge=0.0, le=1.0, description="Normalized Accuracy (Oracle Grade)")
    ai_analysis_grade: float = Field(..., ge=0.0, le=1.0, description="Normalized Confidence (Subjective AI Grade)")
    
    is_risk_detected: bool = Field(default=False, description="Whether a risk was detected in this state")