from dataclasses import dataclass
from typing import List, Tuple
import sqlite3
from .database import execute_query


@dataclass
class Task:
    task_id: str
    difficulty: str
    description: str
    broken_sql: str
    correct_sql: str
    expected_output_hint: str


# ── Easy tasks: syntax errors (typos, missing keywords) ──────────────────────

easy_tasks = [
    Task(
        task_id="easy1",
        difficulty="easy",
        description="Fix keyword typos (SELCT, FORM)",
        broken_sql="SELCT name, salary FORM employees WHERE department = 'Engineering'",
        correct_sql="SELECT name, salary FROM employees WHERE department = 'Engineering'",
        expected_output_hint="Expected columns: name, salary",
    ),
    Task(
        task_id="easy2",
        difficulty="easy",
        description="Fix missing comma in SELECT",
        broken_sql="SELECT name salary FROM employees",
        correct_sql="SELECT name, salary FROM employees",
        expected_output_hint="Expected columns: name, salary",
    ),
    Task(
        task_id="easy3",
        difficulty="easy",
        description="Fix table name typo",
        broken_sql="SELECT * FROM employes WHERE salary > 50000",
        correct_sql="SELECT * FROM employees WHERE salary > 50000",
        expected_output_hint="Expected columns: id, name, department, salary, hire_date",
    ),
    Task(
        task_id="easy4",
        difficulty="easy",
        description="Fix ORDER BY typo",
        broken_sql="SELECT name, department FROM employees ODER BY salary DESC",
        correct_sql="SELECT name, department FROM employees ORDER BY salary DESC",
        expected_output_hint="Expected columns: name, department",
    ),
    Task(
        task_id="easy5",
        difficulty="easy",
        description="Fix COUNT function",
        broken_sql="SELECT COUNT() FROM employees",
        correct_sql="SELECT COUNT(*) FROM employees",
        expected_output_hint="Expected columns: COUNT(*)",
    ),
]

# ── Medium tasks: logic errors (wrong conditions, aggregations) ──────────────

medium_tasks = [
    Task(
        task_id="medium1",
        difficulty="medium",
        description="Fix aggregation function (MIN should be MAX)",
        broken_sql="SELECT department, MIN(salary) FROM employees GROUP BY department",
        correct_sql="SELECT department, MAX(salary) FROM employees GROUP BY department",
        expected_output_hint="Expected output shows max salary per department",
    ),
    Task(
        task_id="medium2",
        difficulty="medium",
        description="Fix WHERE condition (< should be >)",
        broken_sql="SELECT name FROM employees WHERE salary < 70000",
        correct_sql="SELECT name FROM employees WHERE salary > 70000",
        expected_output_hint="Expected output shows employees with salary > 70000",
    ),
    Task(
        task_id="medium3",
        difficulty="medium",
        description="Add missing GROUP BY",
        broken_sql="SELECT department, COUNT(*) FROM employees",
        correct_sql="SELECT department, COUNT(*) FROM employees GROUP BY department",
        expected_output_hint="Expected output shows count per department",
    ),
    Task(
        task_id="medium4",
        difficulty="medium",
        description="Fix ORDER BY direction (ASC should be DESC)",
        broken_sql="SELECT name, salary FROM employees ORDER BY salary ASC",
        correct_sql="SELECT name, salary FROM employees ORDER BY salary DESC",
        expected_output_hint="Expected output ordered by salary descending",
    ),
    Task(
        task_id="medium5",
        difficulty="medium",
        description="Fix JOIN condition",
        broken_sql="SELECT e.name, d.name FROM employees e JOIN departments d ON e.id = d.id",
        correct_sql="SELECT e.name, d.name FROM employees e JOIN departments d ON e.department = d.name",
        expected_output_hint="Expected output shows employee names with their department names",
    ),
]

# ── Hard tasks: structural errors (JOINs, subqueries, HAVING) ───────────────

hard_tasks = [
    Task(
        task_id="hard1",
        difficulty="hard",
        description="Add missing HAVING clause",
        broken_sql="SELECT department, AVG(salary) FROM employees GROUP BY department",
        correct_sql="SELECT department, AVG(salary) FROM employees GROUP BY department HAVING AVG(salary) > 60000",
        expected_output_hint="Expected output shows departments with avg salary > 60000",
    ),
    Task(
        task_id="hard2",
        difficulty="hard",
        description="Fix subquery aggregate (MIN should be AVG)",
        broken_sql="SELECT name FROM employees WHERE salary > (SELECT MIN(salary) FROM employees)",
        correct_sql="SELECT name FROM employees WHERE salary > (SELECT AVG(salary) FROM employees)",
        expected_output_hint="Expected output shows employees with salary > average",
    ),
    Task(
        task_id="hard3",
        difficulty="hard",
        description="Fix JOIN type (INNER should be LEFT)",
        broken_sql="SELECT e.name, p.name FROM employees e INNER JOIN employee_projects ep ON e.id = ep.employee_id INNER JOIN projects p ON ep.project_id = p.id",
        correct_sql="SELECT e.name, p.name FROM employees e LEFT JOIN employee_projects ep ON e.id = ep.employee_id LEFT JOIN projects p ON ep.project_id = p.id",
        expected_output_hint="Expected output shows all employees and their projects (if any)",
    ),
    Task(
        task_id="hard4",
        difficulty="hard",
        description="Fix correlated subquery",
        broken_sql="SELECT name FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees)",
        correct_sql="SELECT name FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE department = e.department)",
        expected_output_hint="Expected output shows employees earning above their department average",
    ),
    Task(
        task_id="hard5",
        difficulty="hard",
        description="Fix missing LIMIT and ORDER BY for top-N query",
        broken_sql="SELECT name, salary FROM employees ORDER BY salary",
        correct_sql="SELECT name, salary FROM employees ORDER BY salary DESC LIMIT 3",
        expected_output_hint="Expected output shows top 3 highest paid employees",
    ),
]

all_tasks = {
    "easy": easy_tasks,
    "medium": medium_tasks,
    "hard": hard_tasks,
}

# TODO: add tasks for INSERT/UPDATE statements, not just SELECT

class TaskGrader:
    """Grade a fixed SQL query against the expected correct query."""

    def grade(self, fixed_sql: str, conn: sqlite3.Connection, task: Task) -> Tuple[float, str]:
        """Grade and clamp score to strictly within (0, 1)."""
        raw_score, feedback = self._compute_raw_score(fixed_sql, conn, task)
        # Clamp to open interval (0, 1) — hackathon requires strictly between 0 and 1
        clamped = max(0.05, min(0.95, raw_score))
        return clamped, feedback

    def _compute_raw_score(self, fixed_sql: str, conn: sqlite3.Connection, task: Task) -> Tuple[float, str]:
        if not fixed_sql or not fixed_sql.strip():
            return 0.0, "No SQL provided"

        fixed_sql = fixed_sql.strip()
        actual_rows, error = execute_query(conn, fixed_sql)
        if error:
            return 0.0, f"SQL error: {error}"

        expected_rows, exp_error = execute_query(conn, task.correct_sql)
        if exp_error:
            return 0.0, f"Internal error running expected SQL: {exp_error}"

        # ── Easy: just needs to execute and return rows ─────────────────
        if task.difficulty == "easy":
            if actual_rows:
                return 1.0, "Query executed and returned rows"
            else:
                return 0.5, "Query executed but returned no rows"

        # ── Medium: compare result sets ─────────────────────────────────
        elif task.difficulty == "medium":
            if actual_rows == expected_rows:
                return 1.0, "Exact match"
            actual_set = set(tuple(row.items()) for row in actual_rows)
            expected_set = set(tuple(row.items()) for row in expected_rows)
            if actual_set == expected_set:
                return 0.7, "Same rows, different order"
            overlap = len(actual_set & expected_set)
            if expected_rows and overlap >= len(expected_rows) * 0.5:
                return 0.3, "At least 50% of expected rows present"
            return 0.0, "No significant match"

        # ── Hard: compare with column-order tolerance ───────────────────
        elif task.difficulty == "hard":
            if actual_rows == expected_rows:
                return 1.0, "Exact match"
            actual_set = set(tuple(sorted(row.items())) for row in actual_rows)
            expected_set = set(tuple(sorted(row.items())) for row in expected_rows)
            if actual_set == expected_set:
                return 0.8, "Same rows, different column order"
            overlap = len(actual_set & expected_set)
            if expected_rows and overlap >= len(expected_rows) * 0.5:
                return 0.5, "At least 50% rows correct"
            if actual_rows:
                return 0.1, "Query executed but results don't match"
            return 0.0, "No results"

        return 0.0, "Unknown difficulty"