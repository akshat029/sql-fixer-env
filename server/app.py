import uvicorn
from openenv.core.env_server import create_app
from models import SQLFixerAction, SQLFixerObservation
from .sql_fixer_environment import SQLFixerEnvironment

app = create_app(
    SQLFixerEnvironment,
    SQLFixerAction,
    SQLFixerObservation,
    env_name="sql_fixer_env",
)


def main():
    """Entry point for the server — required by openenv validate."""
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()