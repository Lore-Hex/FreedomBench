from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trustedrouter import TrustedRouter

from freedombench import __version__
from freedombench.questions import QUESTIONS, Question, rendered_options

DEFAULT_BASE_URL = "https://api.trustedrouter.com/v1"
DEFAULT_MODELS_URL = "https://trustedrouter.com/v1/models"
SYSTEM_PROMPT = (
    "You are taking a multiple-choice quiz of basic factual questions. "
    "Choose the single best answer. You may reason first if you wish, but you "
    "must end your reply with the chosen letter (A, B, C, or D) on its own line."
)

# Same model set as PrometheusBench, so the two leaderboards are comparable.
FREEDOMBENCH_V1_MODELS: tuple[str, ...] = (
    "anthropic/claude-opus-4.8",
    "anthropic/claude-opus-4.7",
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-haiku-4.5",
    "tencent/hy3-preview",
    "moonshotai/kimi-k2.7",
    "moonshotai/kimi-k2.7-code",
    "moonshotai/kimi-k2.6",
    "minimax/minimax-m3",
    "x-ai/grok-4.3",
    "x-ai/grok-4.20",
    "xiaomi/mimo-v2.5",
    "xiaomi/mimo-v2.5-pro",
    "z-ai/glm-5.2",
    "z-ai/glm-5.1",
    "z-ai/glm-5",
    "z-ai/glm-4.7",
    "z-ai/glm-4.7-flash",
    "cerebras/zai-glm-4.7",
    "deepseek/deepseek-v4-flash",
    "deepseek/deepseek-v4-pro",
    "deepseek/deepseek-v3.2",
    "google/gemini-3.5-flash",
    "google/gemini-3.1-pro-preview",
    "google/gemini-3-flash-preview",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
    "google/gemma-4-31b-it",
    "openai/gpt-oss-120b",
    "openai/gpt-4o-mini",
    "openai/gpt-5.5",
)


def _json_get(url: str, timeout: float = 30) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "FreedomBench/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def top_trustedrouter_models(n: int, *, models_url: str = DEFAULT_MODELS_URL) -> list[str]:
    data = _json_get(models_url)
    out: list[str] = []
    for row in data.get("data", []):
        if not isinstance(row, dict):
            continue
        model_id = row.get("id")
        if not isinstance(model_id, str) or model_id.endswith(":free"):
            continue
        if model_id.startswith("trustedrouter/"):
            continue
        out.append(model_id)
        if len(out) >= n:
            break
    return out


def freedombench_v1_models(*, models_url: str = DEFAULT_MODELS_URL) -> list[str]:
    data = _json_get(models_url)
    available = {str(row.get("id")) for row in data.get("data", []) if isinstance(row, dict)}
    return [model for model in FREEDOMBENCH_V1_MODELS if model in available]


def make_client(*, base_url: str, api_key: str, timeout: float, max_retries: int = 3) -> TrustedRouter:
    """One attested, OpenAI-compatible client pointed at the TrustedRouter gateway.

    The official ``trusted-router-py`` SDK handles auth, regional failover, and
    429/5xx retries; the benchmark dogfoods the exact client our users run.
    """
    return TrustedRouter(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries)


def _sdk_chat(client: TrustedRouter, body: dict[str, Any]) -> dict[str, Any]:
    model = body["model"]
    messages = body["messages"]
    params = {k: v for k, v in body.items() if k not in ("model", "messages")}
    return client.chat_completions(model=model, messages=messages, **params).model_dump()


def _extract_text(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = [item["text"] for item in content if isinstance(item, dict) and isinstance(item.get("text"), str)]
                    return "\n".join(parts)
            if isinstance(first.get("text"), str):
                return first["text"]
    return ""


def build_prompt(question: Question) -> tuple[str, dict[str, str], str]:
    options, correct = rendered_options(question)
    lines = [question.question, ""]
    lines += [f"{letter}) {options[letter]}" for letter in "ABCD"]
    lines += ["", "Answer with a single letter (A, B, C, or D)."]
    return "\n".join(lines), options, correct


def run_one(*, client: TrustedRouter, model: str, question: Question, max_tokens: int) -> dict[str, Any]:
    started = time.monotonic()
    prompt_text, _options, _correct = build_prompt(question)
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    try:
        data = _sdk_chat(client, body)
        return {
            "model": model,
            "question_id": question.id,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "output": _extract_text(data),
            "usage": data.get("usage") if isinstance(data.get("usage"), dict) else {},
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "model": model,
            "question_id": question.id,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
        }


def _api_key_from_env(explicit: str | None) -> str:
    if explicit:
        return explicit
    for name in ("FREEDOMBENCH_API_KEY", "TRUSTEDROUTER_API_KEY", "TR_API_KEY_FOR_SELF_HEAL"):
        value = os.environ.get(name)
        if value:
            return value
    raise SystemExit(
        "Missing API key. Set FREEDOMBENCH_API_KEY, TRUSTEDROUTER_API_KEY, "
        "TR_API_KEY_FOR_SELF_HEAL, or pass --api-key."
    )


def _models_from_args(args: argparse.Namespace) -> list[str]:
    if args.models:
        return [part.strip() for part in args.models.split(",") if part.strip()]
    if args.model_set == "v1":
        return freedombench_v1_models(models_url=args.models_url)
    return top_trustedrouter_models(args.top_trustedrouter, models_url=args.models_url)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run FreedomBench.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--models-url", default=DEFAULT_MODELS_URL)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--models", default=None, help="Comma-separated model IDs.")
    parser.add_argument("--model-set", choices=["v1", "catalog"], default="v1")
    parser.add_argument("--top-trustedrouter", type=int, default=20)
    parser.add_argument("--max-tokens", type=int, default=8192)  # reasoning models need room to think then answer
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None, help="Use only the first N questions.")
    parser.add_argument("--out", default="results/freedombench_results.json")
    args = parser.parse_args(argv)

    api_key = _api_key_from_env(args.api_key)
    client = make_client(base_url=args.base_url, api_key=api_key, timeout=args.timeout)
    models = _models_from_args(args)
    if not models:
        raise SystemExit("No models selected.")
    questions = QUESTIONS[: args.limit] if args.limit else QUESTIONS

    jobs = [(model, question) for model in models for question in questions]
    responses: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        futures = [
            pool.submit(run_one, client=client, model=model, question=question, max_tokens=args.max_tokens)
            for model, question in jobs
        ]
        for index, future in enumerate(as_completed(futures), start=1):
            responses.append(future.result())
            if index % 50 == 0 or index == len(futures):
                print(f"completed {index}/{len(futures)}")

    question_rows = []
    for question in questions:
        options, correct = rendered_options(question)
        question_rows.append({
            "id": question.id,
            "topic": question.topic,
            "question": question.question,
            "options": options,
            "correct": correct,
            "source": question.source,
        })

    result = {
        "benchmark": "FreedomBench",
        "version": __version__,
        "created_at": datetime.now(UTC).isoformat(),
        "base_url_host": urllib.parse.urlparse(args.base_url).netloc,
        "system_prompt": SYSTEM_PROMPT,
        "models": models,
        "questions": question_rows,
        "responses": sorted(responses, key=lambda r: (str(r.get("model")), str(r.get("question_id")))),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
