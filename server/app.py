import uvicorn
from pathlib import Path
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openenv.core.env_server import create_app
from models import SQLFixerAction, SQLFixerObservation
from .sql_fixer_environment import SQLFixerEnvironment
from .database import create_database, get_schema_string, execute_query, rows_to_string
from .tasks import all_tasks, TaskGrader

app = create_app(
    SQLFixerEnvironment,
    SQLFixerAction,
    SQLFixerObservation,
    env_name="sql_fixer_env",
)

# ── Static files & Web UI ────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the web UI at the root URL."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>SQL Fixer Environment</h1><p>UI not found.</p>")


@app.get("/api/schema")
async def get_schema():
    """Return the database schema for the UI."""
    return JSONResponse({"schema": get_schema_string()})


@app.post("/api/fix")
async def fix_sql(request: Request):
    """
    Simple UI endpoint: takes broken SQL, finds matching task (or runs as-is),
    grades the fix attempt using the environment grader.
    """
    try:
        body = await request.json()
        broken_sql = body.get("broken_sql", "").strip()

        if not broken_sql:
            return JSONResponse({"error": "No SQL provided"}, status_code=400)

        # Find a matching task
        matched_task = None
        matched_difficulty = None
        for diff, tasks in all_tasks.items():
            for task in tasks:
                if task.broken_sql.strip().lower() == broken_sql.lower():
                    matched_task = task
                    matched_difficulty = diff
                    break
            if matched_task:
                break

        conn = create_database()
        grader = TaskGrader()

        if matched_task:
            # Use the known correct SQL as the fix
            fixed_sql = matched_task.correct_sql
            rows, error = execute_query(conn, fixed_sql)
            score, feedback = grader.grade(fixed_sql, conn, matched_task)
            result = rows_to_string(rows) if not error else f"Error: {error}"

            return JSONResponse({
                "broken_sql": broken_sql,
                "fixed_sql": fixed_sql,
                "score": score,
                "feedback": feedback,
                "result": result,
                "task_id": matched_task.task_id,
                "difficulty": matched_difficulty,
            })
        else:
            # No matching task — just try to execute the user's SQL directly
            rows, error = execute_query(conn, broken_sql)
            if error:
                return JSONResponse({
                    "broken_sql": broken_sql,
                    "fixed_sql": broken_sql,
                    "score": 0.1,
                    "feedback": f"SQL error: {error}. Try one of the example queries!",
                    "result": "",
                    "task_id": None,
                    "difficulty": None,
                })
            else:
                result = rows_to_string(rows)
                return JSONResponse({
                    "broken_sql": broken_sql,
                    "fixed_sql": broken_sql,
                    "score": 0.5,
                    "feedback": "Query executed successfully (no matching task found for grading).",
                    "result": result,
                    "task_id": None,
                    "difficulty": None,
                })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Mount static files last so they don't override API routes
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def main():
    """Entry point for the server — required by openenv validate."""
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()