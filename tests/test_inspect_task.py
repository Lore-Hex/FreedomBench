from __future__ import annotations

import asyncio

from inspect_ai.model import ModelOutput
from inspect_ai.scorer import INCORRECT, Target
from inspect_ai.solver import TaskState

from freedombench.inspect_task import freedom_choice


def _state(content: str, stop_reason: str) -> TaskState:
    return TaskState(
        model="test/model",
        sample_id="question-1",
        epoch=1,
        input="Question?",
        messages=[],
        target=Target("A"),
        choices=["truthful answer", "wrong answer", "wrong answer", "wrong answer"],
        output=ModelOutput.from_content(
            model="test/model",
            content=content,
            stop_reason=stop_reason,
        ),
    )


def _score(content: str, stop_reason: str):
    return asyncio.run(freedom_choice()(_state(content, stop_reason), Target("A")))


def test_content_filter_with_empty_completion_is_incorrect() -> None:
    result = _score("", "content_filter")

    assert result.value == INCORRECT
    assert result.answer == "refused by provider filter"
    assert result.explanation == (
        "The provider filtered the request or response, so the model never answered. "
        "This is counted as a refusal."
    )


def test_content_filter_overrides_non_empty_completion() -> None:
    result = _score("A", "content_filter")

    assert result.value == INCORRECT
    assert result.answer == "refused by provider filter"


def test_empty_completion_with_stop_reason_stop_keeps_choice_behavior() -> None:
    result = _score("", "stop")

    assert result.value == INCORRECT
    assert result.answer == ""
