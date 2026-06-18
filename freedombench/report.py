from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from freedombench.classify import expected_question_count, summarize_results

START = "<!-- FREEDOMBENCH_RESULTS_START -->"
END = "<!-- FREEDOMBENCH_RESULTS_END -->"
FONT = 'font-family="Inter, Arial, sans-serif"'

# Chinese labs whose OWN hosted API TrustedRouter routes to (so the row reflects
# that lab's censorship). Qwen/MiniMax/Tencent have no own-API route here.
CHINESE_LAB_ORGS = {"z-ai", "deepseek", "moonshotai", "xiaomi"}


def _load_providers() -> dict[str, dict[str, Any]]:
    p = Path(__file__).parent / "providers.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _fmt(value: Any) -> str:
    return f"{value:.1f}" if isinstance(value, float) else str(value)


def _served_by(model: str, providers: dict[str, dict[str, Any]]) -> tuple[str, bool]:
    info = providers.get(model, {})
    return str(info.get("provider", "?")), bool(info.get("lab_own"))


def _bar_color(score: int, max_score: int) -> str:
    if score >= max_score * 0.8:
        return "#16a34a"  # green: answers freely / truthfully
    if score >= max_score * 0.4:
        return "#f97316"  # orange
    return "#dc2626"  # red: censored / refuses


def markdown_table(rows: list[dict[str, Any]], providers: dict[str, dict[str, Any]], *, limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    lines = [
        "| Rank | Model | Served by | Correct | Freedom % | Refused | Errors |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for index, row in enumerate(selected, start=1):
        prov, lab_own = _served_by(row["model"], providers)
        served = prov if lab_own else f"{prov} †"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    f"`{row['model']}`",
                    served,
                    str(row["correct"]),
                    _fmt(row["freedom_rate"]),
                    str(row["refused"]),
                    str(row["errors"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def lab_api_table(rows: list[dict[str, Any]], providers: dict[str, dict[str, Any]]) -> str:
    """Chinese models served by their own lab API — what the maker itself censors."""
    sub = [
        r
        for r in rows
        if _served_by(r["model"], providers)[1] and r["model"].split("/")[0] in CHINESE_LAB_ORGS
    ]
    lines = [
        "| Lab (own API) | Model | Freedom % | Refused |",
        "|---|---|---:|---:|",
    ]
    for r in sub:
        prov, _ = _served_by(r["model"], providers)
        lines.append(f"| {prov} | `{r['model']}` | {_fmt(r['freedom_rate'])} | {r['refused']} |")
    return "\n".join(lines)


CAVEAT = (
    "**How to read this — source vs. host.** Censorship is applied at the serving host, not baked "
    "into most open weights: the same GLM-4.7 weights refuse 27 of these questions on Z.ai's own "
    "API but answer all 27 on Cerebras. TrustedRouter routes each model to a provider — sometimes "
    "the lab's own API, sometimes a neutral third-party host. Rows on the **lab's own API** (z-ai, "
    "deepseek, kimi, xiaomi, and the Western labs) reflect that lab's censorship. Rows marked **†** "
    "are served by a **third-party host** (Qwen via Novita/Together/Parasail, MiniMax & Hunyuan via "
    "SiliconFlow, GLM via Cerebras) and therefore measure the open weights, *not* the lab's own API — "
    "so they under-detect a lab that censors only at its own endpoint. Alibaba (Qwen), MiniMax, and "
    "Tencent have no own-API route here, so their scores below are weights-on-a-neutral-host, not the lab."
)


def _svg_bar_chart(
    rows: list[dict[str, Any]],
    providers: dict[str, dict[str, Any]],
    *,
    max_score: int | None = None,
    title: str = "FreedomBench score",
    subtitle: str = "China-censored facts answered truthfully (of 60). † = third-party host (measures the weights, not the lab).",
) -> str:
    if max_score is None:
        max_score = max(1, expected_question_count())
    display = list(rows)
    row_h = 27
    top = 52
    left = 340
    width = 1020
    height = top + row_h * len(display) + 52
    max_bar = 410
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="24" y="30" {FONT} font-size="22" font-weight="700" fill="#111827">{html.escape(title)}</text>',
        f'<text x="24" y="50" {FONT} font-size="12" fill="#4b5563">{html.escape(subtitle)}</text>',
    ]
    for index, row in enumerate(display):
        y = top + index * row_h
        score = int(row["raw_score"])
        bar_w = max(1, int(max_bar * score / max_score))
        color = _bar_color(score, max_score)
        prov, lab_own = _served_by(str(row["model"]), providers)
        tag = prov if lab_own else f"{prov} †"
        model = html.escape(f"{row['model']}  ({tag})")
        parts.extend(
            [
                f'<text x="24" y="{y + 17}" {FONT} font-size="12" fill="#111827">{index + 1}. {model}</text>',
                f'<rect x="{left}" y="{y + 4}" width="{max_bar}" height="16" rx="4" fill="#e5e7eb"/>',
                f'<rect x="{left}" y="{y + 4}" width="{bar_w}" height="16" rx="4" fill="{color}"/>',
                f'<text x="{left + max_bar + 14}" y="{y + 17}" {FONT} font-size="12" font-weight="700" fill="#111827">{score}</text>',
            ]
        )
    parts.append("</svg>")
    return "\n".join(parts)


def results_block(rows: list[dict[str, Any]], header: str, providers: dict[str, dict[str, Any]], *, svg_path: str) -> str:
    return "\n\n".join(
        [
            START,
            header,
            CAVEAT,
            f"![FreedomBench score chart]({svg_path})",
            "### Best available host (what you get through TrustedRouter)",
            markdown_table(rows, providers),
            "**†** third-party host — measures the open weights, not the lab's own API.",
            "### Censorship at the Chinese labs' own APIs",
            "_Only the labs whose own API TrustedRouter routes to. Alibaba (Qwen), MiniMax, and "
            "Tencent are absent — no own-API route exists here, so their rows above are the weights "
            "on a neutral host, which strip any host-applied censorship._",
            lab_api_table(rows, providers),
            END,
        ]
    )


def update_readme(readme: Path, block: str) -> None:
    text = readme.read_text(encoding="utf-8")
    if START not in text or END not in text:
        text = text.rstrip() + "\n\n" + START + "\n" + END + "\n"
    before, rest = text.split(START, 1)
    _old, after = rest.split(END, 1)
    readme.write_text(before.rstrip() + "\n\n" + block + after, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate FreedomBench report artifacts.")
    parser.add_argument("results")
    parser.add_argument("--svg", default="assets/freedombench_scores.svg")
    parser.add_argument("--readme", default="README.md")
    args = parser.parse_args(argv)

    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    rows = summarize_results(results)
    providers = _load_providers()

    svg_path = Path(args.svg)
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(_svg_bar_chart(rows, providers), encoding="utf-8")

    created = str(results.get("created_at", "unknown"))
    host = str(results.get("base_url_host", "unknown"))
    version = str(results.get("version", "unknown"))
    model_count = len(results.get("models", []))
    question_count = len(results.get("questions", [])) or expected_question_count()
    header = (
        f"FreedomBench v1 snapshot: `{created}` via `{host}`. "
        f"Scored {model_count} models on {question_count} questions. Package version `{version}`."
    )
    block = results_block(rows, header, providers, svg_path=svg_path.as_posix())
    update_readme(Path(args.readme), block)
    print(f"wrote {svg_path} and updated {args.readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
