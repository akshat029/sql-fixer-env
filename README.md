---
title: SQL Fixer Environment
emoji: 🔧
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# SQL Query Fixer Environment - I built this because debugging SQL queries is one of the most common things developers deal with daily. I wanted to see if an AI agent could learn to spot and fix these mistakes automatically.


## Overview

An OpenEnv environment that presents an AI agent with broken SQL queries and challenges it to fix them so they execute correctly against a SQLite database and return expected results. Built for the **Meta × PyTorch OpenEnv Hackathon**.

## Problem Solved

Data analysts and developers frequently encounter broken SQL queries. This environment simulates that real-world debugging task across three difficulty levels, requiring agents to understand database schemas, identify errors, and produce correct SQL.

## Environment Description

| Method    | What it does |
|-----------|-------------|
| `reset()` | Initialises a new episode with a random broken SQL query from the selected difficulty. |
| `step()`  | Takes the agent's fixed SQL query, executes it, compares to expected results, and returns reward + feedback. |
| `state()` | Returns episode ID and step count. |

## Action Space

| Field       | Type   | Description |
|-------------|--------|-------------|
| `broken_sql`| string | The broken SQL query shown to the agent |
| `fixed_sql` | string | The agent's corrected SQL query |
| `task_id`   | string | The task identifier (easy1, medium3, etc.) |

## Observation Space

| Field                | Type   | Description |
|----------------------|--------|-------------|
| `task_id`            | string | Current task identifier |
| `difficulty`         | string | Difficulty level (easy, medium, hard) |
| `schema`             | string | Full CREATE TABLE statements |
| `broken_sql`         | string | The broken SQL query to fix |
| `error_message`      | string | Error from running the broken query |
| `expected_output_hint`| string | Hint about expected output |
| `result`             | string | Result from running the fixed query |
| `success`            | bool   | Whether the fix was successful |
| `feedback`           | string | Human-readable feedback |

## Tasks (3 difficulties)

### Easy — Syntax Error Fixer
Fix queries with simple syntax errors: typos in keywords, missing commas, wrong table names.
**Grading**: 0.95 if executes and returns rows · 0.5 if executes but empty · 0.05 if fails.

### Medium — Logic Error Fixer
Fix queries with logical errors: wrong WHERE conditions, missing GROUP BY, wrong aggregations.
**Grading**: 0.95 exact match · 0.7 same rows different order · 0.3 ≥50% expected rows · 0.1 otherwise.

### Hard — Structural Query Rewriter
Fix queries with structural errors: wrong JOINs, subquery bugs, missing HAVING.
**Grading**: 0.95 exact match · 0.8 same rows different columns · 0.5 ≥50% rows · 0.15 executes but not useful · 0.05 fails.

## Setup Instructions

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the environment server

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### 3. Run inference

```bash
# Set your API key
export HF_TOKEN="your-api-key"
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"

python inference.py
```

The inference script will auto-start the server if `ENV_URL` is not set.

## Environment Variables

| Variable       | Description                          | Default |
|----------------|--------------------------------------|---------|
| `API_BASE_URL` | LLM API endpoint                     | `https://api.openai.com/v1` |
| `MODEL_NAME`   | Model identifier                     | `gpt-4o-mini` |
| `HF_TOKEN`     | API key for LLM authentication       | *(required)* |
| `ENV_URL`      | URL of the deployed environment      | `http://localhost:7860` |

## Docker

```bash
docker build -t sql-fixer-env .
docker run -p 7860:7860 sql-fixer-env
```

## Hugging Face Space

Deployed at: `https://huggingface.co/spaces/YOUR_HF_USERNAME/sql-fixer-env`