from typing import Any, Dict

from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from models import SQLFixerAction, SQLFixerObservation


class SQLFixerEnv(EnvClient[SQLFixerAction, SQLFixerObservation, State]):
    """Client for the SQL Fixer OpenEnv environment."""

    def _step_payload(self, action: SQLFixerAction) -> Dict[str, Any]:
        return action.model_dump()

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[SQLFixerObservation]:
        obs_data = payload.get("observation", payload)
        observation = SQLFixerObservation(**obs_data)
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> State:
        return State(**payload)