"""
SQL Fixer Environment — Inference Script
Connects to the OpenEnv server, uses an LLM to fix broken SQL queries,
and emits structured [START] / [STEP] / [END] logs for evaluation.
"""

import os
import sys
import json
import time
import datetime
import subprocess
import signal
import atexit

from openai import OpenAI

# ── Environment variables (mandatory per hackathon spec) ─────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
# tried using gpt-4o here first but switched to llama for free tier

# Where the environment server is running
ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")

# ── Helpers ──────────────────────────────────────────────────────────────────

def log(marker: str, data: dict):
    """Print a structured log line: [START|STEP|END] {json}"""
    data["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    print(f"{marker} {json.dumps(data)}")
    sys.stdout.flush()


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


# ── Main inference logic ─────────────────────────────────────────────────────

def run_inference():
    # Lazy-import the client (needs openenv-core)
    from client import SQLFixerEnv
    from models import SQLFixerAction

    llm = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

    log("[START]", {
        "event": "inference_started",
        "model": MODEL_NAME,
        "env_url": ENV_URL,
    })

    task_ids = ["easy", "medium", "hard"]
    episodes_per_task = 3
    all_results = {}

    # Use synchronous client
    with SQLFixerEnv(base_url=ENV_URL).sync() as env:
        for task_id in task_ids:
            scores = []
            for ep in range(episodes_per_task):
                step_start = time.time()
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
                    # Clamp to strictly (0, 1) for evaluator compliance
                    reward = max(0.01, min(0.99, reward))
                    scores.append(reward)

                    log("[STEP]", {
                        "task_id": task_id,
                        "episode": ep + 1,
                        "reward": reward,
                        "done": step_result.done,
                        "feedback": step_result.observation.feedback,
                        "duration_s": round(time.time() - step_start, 2),
                    })

                except Exception as e:
                    scores.append(0.05)
                    log("[STEP]", {
                        "task_id": task_id,
                        "episode": ep + 1,
                        "reward": 0.05,
                        "done": True,
                        "error": str(e),
                        "duration_s": round(time.time() - step_start, 2),
                    })

            all_results[task_id] = scores

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n=== SQL FIXER ENVIRONMENT — INFERENCE RESULTS ===")
    total_scores = []
    summary = {}
    for task_id in task_ids:
        scores = all_results[task_id]
        avg = sum(scores) / len(scores) if scores else 0.0
        summary[task_id] = {"avg_reward": round(avg, 3), "scores": scores}
        print(f"  Task: {task_id:8s} | Episodes: {len(scores)} | "
              f"Avg: {avg:.2f} | Min: {min(scores):.1f} | Max: {max(scores):.1f}")
        total_scores.extend(scores)

    overall = sum(total_scores) / len(total_scores) if total_scores else 0.0
    print(f"  Overall Avg Score: {overall:.3f}")
    print("=" * 50)

    log("[END]", {
        "event": "inference_completed",
        "overall_avg_reward": round(overall, 3),
        "task_summary": summary,
    })


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # If no ENV_URL is set, start the server locally in the background
    server_proc = None
    if not os.environ.get("ENV_URL"):
        print("Starting local environment server...")
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