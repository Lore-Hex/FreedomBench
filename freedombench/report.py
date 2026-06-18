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


def _fmt(value: Any) -> str:
    return f"{value:.1f}" if isinstance(value, float) else str(value)


def _bar_color(score: int, max_score: int) -> str:
    if score >= max_score * 0.8:
        return "#16a34a"  # green: answers freely / truthfully
    if score >= max_score * 0.4:
        return "#f97316"  # orange
    return "#dc2626"  # red: censored / refuses


def markdown_table(rows: list[dict[str, Any]], *, limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    lines = [
        "| Rank | Model | Correct | Freedom % | Incorrect | Refused | Errors |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for index, row in enumerate(selected, start=1):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    f"`{row['model']}`",
                    str(row["correct"]),
                    _fmt(row["freedom_rate"]),
                    str(row["incorrect"]),
                    str(row["refused"]),
                    str(row["errors"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _svg_bar_chart(
    rows: list[dict[str, Any]],
    *,
    max_score: int | None = None,
    title: str = "FreedomBench score",
    subtitle: str = "China-censored factual questions answered truthfully (of 60). Higher means freer.",
) -> str:
    if max_score is None:
        max_score = max(1, expected_question_count())
    display = list(rows)
    row_h = 27
    top = 52
    left = 280
    width = 960
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
        model = html.escape(str(row["model"]))
        label = f"{score}/{max_score} truthful"
        parts.extend(
            [
                f'<text x="24" y="{y + 17}" {FONT} font-size="12" fill="#111827">{index + 1}. {model}</text>',
                f'<rect x="{left}" y="{y + 4}" width="{max_bar}" height="16" rx="4" fill="#e5e7eb"/>',
                f'<rect x="{left}" y="{y + 4}" width="{bar_w}" height="16" rx="4" fill="{color}"/>',
                f'<text x="{left + max_bar + 14}" y="{y + 17}" {FONT} font-size="12" font-weight="700" fill="#111827">{score}</text>',
                f'<text x="{left + max_bar + 56}" y="{y + 17}" {FONT} font-size="12" fill="#4b5563">{label}</text>',
            ]
        )
    parts.append("</svg>")
    return "\n".join(parts)


def results_block(rows: list[dict[str, Any]], header: str, *, svg_path: str) -> str:
    return "\n\n".join(
        [
            START,
            header,
            f"![FreedomBench score chart]({svg_path})",
            markdown_table(rows),
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

    svg_path = Path(args.svg)
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(_svg_bar_chart(rows), encoding="utf-8")

    created = str(results.get("created_at", "unknown"))
    host = str(results.get("base_url_host", "unknown"))
    version = str(results.get("version", "unknown"))
    model_count = len(results.get("models", []))
    question_count = len(results.get("questions", [])) or expected_question_count()
    header = (
        f"FreedomBench v1 snapshot: `{created}` via `{host}`. "
        f"Scored {model_count} models on {question_count} questions. Package version `{version}`."
    )
    block = results_block(rows, header, svg_path=svg_path.as_posix())
    update_readme(Path(args.readme), block)
    print(markdown_table(rows))
    print(f"wrote {svg_path} and updated {args.readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
