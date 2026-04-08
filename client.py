# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Legal Auditor Env Environment Client."""

from typing import Dict
import os

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import LegalAuditorAction, LegalAuditorObservation


class LegalAuditorEnv(
    EnvClient[LegalAuditorAction, LegalAuditorObservation, State]
):
    """
    Client for the Legal Auditor Env Environment.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions with lower latency.
    """

    def _step_payload(self, action: LegalAuditorAction) -> Dict:
        """
        Convert LegalAuditorAction to JSON payload for step message.
        Matches the 'action' field in LegalAuditorAction model.
        """
        return {
            "action": action.action,  # FIXED: changed from action_type to action
            "rationale": getattr(action, 'rationale', None), 
        }

    def _parse_result(self, payload: Dict) -> StepResult[LegalAuditorObservation]:
        """
        Parse server response into StepResult[LegalAuditorObservation].
        Syncs exactly with LegalAuditorObservation model fields.
        """
        obs_data = payload.get("observation", {})
        
        # FIXED: Mapping the actual fields returned by LegalAuditorEnvironment
        observation = LegalAuditorObservation(
            clause_text=obs_data.get("clause_text", ""),
            clause_index=obs_data.get("clause_index", 0),
            agent_reliability=obs_data.get("agent_reliability", 0.0),
            ai_analysis_grade=obs_data.get("ai_analysis_grade", 0.0),
            is_risk_detected=obs_data.get("is_risk_detected", False)
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """
        Parse server response into State object.
        """
        return State(
            episode_id=payload.get("episode_id", "unknown"),
            step_count=payload.get("step_count", 0),
        )