from openenv.core.env_server.types import Action, Observation


class SQLFixerAction(Action):
    """Action: the agent submits a fixed SQL query."""
    broken_sql: str
    fixed_sql: str
    task_id: str


class SQLFixerObservation(Observation):
    """Observation returned by the environment.

    Inherits `done`, `reward`, and `metadata` from Observation base class.
    """
    task_id: str = ""
    difficulty: str = ""
    db_schema: str = ""
    broken_sql: str = ""
    error_message: str = ""
    expected_output_hint: str = ""
    result: str = ""
    success: bool = False
    feedback: str = ""