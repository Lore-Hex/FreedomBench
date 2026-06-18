"""Definitive SERIAL (concurrency=1) re-run on the final question set.

Confidence over speed, per the owner's instruction: every call goes out one at a
time, with retry-on-no-letter (empty OR partial/truncated completions are retried;
a decided wrong answer is never retried). To keep concurrency-1 tractable:

  * SUSPECT models (anything that scored < 100% at conc-16, where load artifacts
    could have mattered) are re-run on ALL 60 questions.
  * The already-clean 100% models are re-run ONLY on questions whose text changed
    (CHANGED_IDS) — their other answers are reused from the prior run, since a
    100% score has no artifact to clean and re-running them serially is pure cost.

Writes a fresh full results JSON in the standard schema; merges nothing in place.
"""
from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from freedombench import __version__
from freedombench.questions import QUESTIONS, rendered_options
from freedombench.run import DEFAULT_BASE_URL, SYSTEM_PROMPT, make_client, run_one

PRIOR = Path(os.environ.get("PRIOR", "results/freedombench_v1.json"))
OUT = Path(os.environ.get("OUT", "results/freedombench_serial.json"))
EMPTY_RETRIES = int(os.environ.get("EMPTY_RETRIES", "6"))
CHANGED_IDS = {s.strip() for s in os.environ.get("CHANGED_IDS", "").split(",") if s.strip()}

# Models that scored < 100% at conc-16 → re-run in full, serially.
SUSPECT = {
    "deepseek/deepseek-v4-pro",
    "google/gemini-3.5-flash",
    "openai/gpt-oss-120b",
    "tencent/hy3-preview",
    "xiaomi/mimo-v2.5",
    "xiaomi/mimo-v2.5-pro",
    "cerebras/zai-glm-4.7",
    "moonshotai/kimi-k2.7-code",
    "z-ai/glm-5.2",
    "z-ai/glm-4.7",
    "z-ai/glm-5.1",
    "z-ai/glm-5",
}

# Extra models not in the v1 panel — historical family versions for the blog's
# per-version decline plot. They are SUSPECT (full serial run, no prior to reuse)
# and are excluded from the v1 leaderboard later; here only to chart the trajectory.
EXTRA = [m.strip() for m in os.environ.get("EXTRA_MODELS", "").split(",") if m.strip()]

prior = json.loads(PRIOR.read_text())
prior_resp = {(r.get("model"), r.get("question_id")): r for r in prior.get("responses", [])}
models = list(prior.get("models", []))
for m in EXTRA:
    if m not in models:
        models.append(m)
SUSPECT = SUSPECT | set(EXTRA)

key = os.environ.get("TRUSTEDROUTER_API_KEY") or os.environ.get("FREEDOMBENCH_API_KEY")
if not key:
    raise SystemExit("set TRUSTEDROUTER_API_KEY")
client = make_client(base_url=DEFAULT_BASE_URL, api_key=key, timeout=120)

print(f"models={len(models)} suspect={len(SUSPECT)} changed_ids={sorted(CHANGED_IDS)} empty_retries={EMPTY_RETRIES}", flush=True)

# RESUME=1: reuse every SUCCESSFUL prior response (output present, no error) and
# only re-run the failures/missing — used to finish a run that died on a 402, so a
# credit top-up only pays for the calls that actually failed.
RESUME = os.environ.get("RESUME") == "1"

responses: list[dict] = []
reran = reused = 0
for model in models:
    full = model in SUSPECT
    for q in QUESTIONS:
        prev = prior_resp.get((model, q.id))
        prev_ok = bool(prev and prev.get("output") and not prev.get("error"))
        if RESUME:
            do_rerun = not prev_ok
        else:
            do_rerun = full or q.id in CHANGED_IDS or prev is None
        if do_rerun:
            r = run_one(client=client, model=model, question=q, max_tokens=8192, empty_retries=EMPTY_RETRIES)
            reran += 1
        else:
            r = prev
            reused += 1
        responses.append(r)
    done = sum(1 for x in responses if not x.get("error"))
    print(f"  {model}: total responses so far {len(responses)} (reran {reran} reused {reused})", flush=True)
    OUT.write_text(json.dumps({"_partial": True, "responses": responses}, indent=1))  # checkpoint

question_rows = []
for q in QUESTIONS:
    options, correct = rendered_options(q)
    question_rows.append({"id": q.id, "topic": q.topic, "question": q.question,
                          "options": options, "correct": correct, "source": q.source})

result = {
    "benchmark": "FreedomBench",
    "version": __version__,
    "created_at": datetime.now(UTC).isoformat(),
    "base_url_host": "api.trustedrouter.com",
    "system_prompt": SYSTEM_PROMPT,
    "run_mode": f"serial concurrency=1, empty_retries={EMPTY_RETRIES}",
    "models": models,
    "questions": question_rows,
    "responses": sorted(responses, key=lambda r: (str(r.get("model")), str(r.get("question_id")))),
}
OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(f"DONE reran={reran} reused={reused} -> {OUT}", flush=True)
