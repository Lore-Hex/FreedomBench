"""Measure run-to-run variance of refusals for the GLM family and the near-top models.

Runs each model ROUNDS times at low concurrency with retry-on-no-letter, and records
the choice each question got on each round. This separates *consistent* refusals (a
model that stays silent on a topic every round = real censorship) from *flaky* ones
(empty/partial under load = artifact). Writes results/variance_probe.json incrementally.
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from freedombench.classify import extract_choice
from freedombench.questions import QUESTIONS, rendered_options
from freedombench.run import DEFAULT_BASE_URL, make_client, run_one

MODELS = [
    "z-ai/glm-5",
    "z-ai/glm-5.1",
    "z-ai/glm-5.2",
    "z-ai/glm-4.7",
    "deepseek/deepseek-v4-pro",
    "google/gemini-3.5-flash",
    "openai/gpt-oss-120b",
]
ROUNDS = int(os.environ.get("ROUNDS", "3"))
CONC = int(os.environ.get("CONC", "2"))
OUT = Path(os.environ.get("OUT", "results/variance_probe.json"))

correct_by_id = {}
topic_by_id = {}
for _q in QUESTIONS:
    _, _c = rendered_options(_q)
    correct_by_id[_q.id] = _c
    topic_by_id[_q.id] = _q.topic

key = os.environ.get("TRUSTEDROUTER_API_KEY") or os.environ.get("FREEDOMBENCH_API_KEY")
if not key:
    raise SystemExit("set TRUSTEDROUTER_API_KEY")
client = make_client(base_url=DEFAULT_BASE_URL, api_key=key, timeout=120)

data: dict = {"created_at": datetime.now(UTC).isoformat(), "rounds": ROUNDS, "conc": CONC, "models": {}}
OUT.parent.mkdir(parents=True, exist_ok=True)

for model in MODELS:
    rounds_data = []
    for rnd in range(ROUNDS):
        per_q: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=CONC) as pool:
            futs = {pool.submit(run_one, client=client, model=model, question=q, max_tokens=8192): q for q in QUESTIONS}
            for fut in as_completed(futs):
                q = futs[fut]
                r = fut.result()
                err = r.get("error")
                ch = None if err else extract_choice(r.get("output") or "")
                per_q[q.id] = {"choice": ch, "correct": correct_by_id[q.id], "topic": topic_by_id[q.id], "err": err}
        c = sum(1 for v in per_q.values() if v["choice"] == v["correct"])
        w = sum(1 for v in per_q.values() if v["choice"] is not None and v["choice"] != v["correct"])
        ref = sum(1 for v in per_q.values() if v["choice"] is None and not v["err"])
        e = sum(1 for v in per_q.values() if v["err"])
        rounds_data.append({"correct": c, "wrong": w, "refused": ref, "errors": e, "per_q": per_q})
        print(f"{model} round {rnd + 1}/{ROUNDS}: correct={c} wrong={w} refused={ref} err={e}", flush=True)
    data["models"][model] = rounds_data
    OUT.write_text(json.dumps(data, indent=1))

print("DONE", flush=True)
