"""
SQL Fixer Environment — Inference Script
=========================================
MANDATORY
- Before submitting, ensure the following variables are defined in your environment configuration:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.

STDOUT FORMAT
- The script emits exactly three line types to stdout, in this order:

    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

  Each task (easy, medium, hard) gets its own [START]...[END] block.
  Scores are strictly in (0, 1).
"""

import os
import sys
import time
import subprocess
import atexit
from typing import List, Optional

from openai import OpenAI

# ── Environment variables (mandatory per hackathon spec) ─────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("API_KEY", "")

# Where the environment server is running
ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")

BENCHMARK = "sql-fixer-env"
EPISODES_PER_TASK = 3
MAX_STEPS = 1  # Each episode is a single step: submit the fixed SQL
SUCCESS_THRESHOLD = 0.5


# ── Structured log helpers (flat key=value format) ───────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    # Sanitize action string: remove newlines, limit length
    action_clean = action.replace("\n", " ").replace("\r", "")[:200]
    print(
        f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def clean_sql(text: str) -> str:
    """Strip markdown fences and whitespace from LLM output."""
    text = text.strip()
    if text.startswith("```sql"):
        text = text[6:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def clamp_score(score: float) -> float:
    """Clamp score to strictly within (0, 1) — never exactly 0 or 1."""
    return max(0.05, min(0.95, score))


# ── Main inference logic ─────────────────────────────────────────────────────

def run_inference():
    # Lazy-import the client (needs openenv-core)
    from client import SQLFixerEnv
    from models import SQLFixerAction

    llm = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

    task_ids = ["easy", "medium", "hard"]

    # Use synchronous client
    with SQLFixerEnv(base_url=ENV_URL).sync() as env:
        for task_id in task_ids:
            rewards: List[float] = []
            steps_taken = 0

            # ── [START] for this task ────────────────────────────────
            log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

            try:
                for ep in range(1, EPISODES_PER_TASK + 1):
                    try:
                        # Reset environment for this task
                        result = env.reset(difficulty=task_id)
                        obs = result.observation

                        # Build LLM prompt
                        prompt = (
                            "You are an expert SQL debugger. You will be given a broken SQL query "
                            "and must return ONLY the corrected SQL query — no explanation, "
                            "no markdown, no backticks.\n\n"
                            f"Database Schema:\n{obs.db_schema}\n\n"
                            f"Broken SQL Query:\n{obs.broken_sql}\n\n"
                            f"Error (if any):\n{obs.error_message}\n\n"
                            f"Hint about expected output:\n{obs.expected_output_hint}\n\n"
                            "Return ONLY the corrected SQL query:"
                        )

                        # Call LLM
                        response = llm.chat.completions.create(
                            model=MODEL_NAME,
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=500,
                            temperature=0.0,
                        )
                        fixed_sql = clean_sql(response.choices[0].message.content)

                        # Submit action
                        action = SQLFixerAction(
                            broken_sql=obs.broken_sql,
                            fixed_sql=fixed_sql,
                            task_id=obs.task_id,
                        )
                        step_result = env.step(action)
                        reward = step_result.reward if step_result.reward is not None else 0.05
                        reward = clamp_score(reward)
                        done = step_result.done if step_result.done is not None else True

                        rewards.append(reward)
                        steps_taken = ep

                        log_step(
                            step=ep,
                            action=fixed_sql,
                            reward=reward,
                            done=done,
                            error=None,
                        )

                    except Exception as e:
                        reward = 0.05
                        rewards.append(reward)
                        steps_taken = ep

                        log_step(
                            step=ep,
                            action="error",
                            reward=reward,
                            done=True,
                            error=str(e).replace("\n", " ")[:200],
                        )

                # ── [END] for this task ──────────────────────────────
                score = sum(rewards) / len(rewards) if rewards else 0.05
                score = clamp_score(score)
                success = score >= SUCCESS_THRESHOLD

                log_end(
                    success=success,
                    steps=steps_taken,
                    score=score,
                    rewards=rewards,
                )

            except Exception as e:
                # Ensure [END] is always emitted even on catastrophic failure
                if not rewards:
                    rewards = [0.05]
                log_end(
                    success=False,
                    steps=max(steps_taken, 1),
                    score=0.05,
                    rewards=rewards,
                )


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # If no ENV_URL is set, start the server locally in the background
    server_proc = None
    if not os.environ.get("ENV_URL"):
        print("Starting local environment server...", flush=True)
        server_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server.app:app",
             "--host", "0.0.0.0", "--port", "7860"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        atexit.register(lambda: server_proc.terminate() if server_proc else None)
        # Wait for server startup
        time.sleep(3)

    try:
        run_inference()
    finally:
        if server_proc:
            server_proc.terminate()
            server_proc.wait(timeout=5)