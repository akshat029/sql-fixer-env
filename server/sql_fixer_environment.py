from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State
from typing import Optional, Any
import uuid
import random

from .database import create_database, get_schema_string, execute_query, rows_to_string
from .tasks import all_tasks, TaskGrader
from models import SQLFixerAction, SQLFixerObservation


class SQLFixerEnvironment(Environment):
    """OpenEnv environment that presents broken SQL queries for an agent to fix."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._conn = None
        self._current_task = None
        self._task_grader = TaskGrader()
        self._current_difficulty = "easy"
        self._state = State(episode_id=str(uuid.uuid4()), step_count=0)

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> SQLFixerObservation:
        """Reset: pick a random broken SQL task for the given difficulty."""
        difficulty = kwargs.get("difficulty", "easy")
        self._current_difficulty = difficulty

        if seed is not None:
            random.seed(seed)

        self._conn = create_database()
        tasks = all_tasks[self._current_difficulty]
        self._current_task = random.choice(tasks)
        self._state = State(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
        )

        # Try executing the broken SQL to capture its error
        _, error = execute_query(self._conn, self._current_task.broken_sql)
        error_message = error if error else ""

        return SQLFixerObservation(
            task_id=self._current_task.task_id,
            difficulty=self._current_difficulty,
            db_schema=get_schema_string(),
            broken_sql=self._current_task.broken_sql,
            error_message=error_message,
            expected_output_hint=self._current_task.expected_output_hint,
            result="",
            reward=None,
            done=False,
            success=False,
            feedback="Episode started. Fix the broken SQL query.",
        )

    def step(
        self,
        action: SQLFixerAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> SQLFixerObservation:
        """Step: grade the agent's fixed SQL query."""
        # Auto-initialize if step is called on a fresh instance (HTTP mode)
        if self._conn is None or self._current_task is None:
            self._conn = create_database()
            # Find the task by task_id from the action
            found = False
            for diff, tasks in all_tasks.items():
                for t in tasks:
                    if t.task_id == action.task_id:
                        self._current_task = t
                        self._current_difficulty = diff
                        found = True
                        break
                if found:
                    break
            if not found:
                # Fallback: pick first easy task
                self._current_difficulty = "easy"
                self._current_task = all_tasks["easy"][0]

        rows, error = execute_query(self._conn, action.fixed_sql)
        reward, feedback = self._task_grader.grade(
            action.fixed_sql, self._conn, self._current_task
        )
        result = rows_to_string(rows) if not error else f"Error: {error}"
        self._state.step_count += 1

        return SQLFixerObservation(
            task_id=self._current_task.task_id,
            difficulty=self._current_difficulty,
            db_schema=get_schema_string(),
            broken_sql=self._current_task.broken_sql,
            error_message="",
            expected_output_hint=self._current_task.expected_output_hint,
            result=result,
            reward=reward,
            done=True,
            success=reward > 0.5,
            feedback=feedback,
        )

    @property
    def state(self) -> State:
        return self._state