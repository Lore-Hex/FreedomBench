"""FreedomBench as an Inspect task, so a run of it can be published with its trace.

The 60 questions, their options and the correct letter all come from
`freedombench.questions` — the same data and the same deterministic per-id shuffle
the standalone runner uses. Nothing is re-stated here: a second copy of a benchmark's
items is a second benchmark that drifts, and the shuffle in particular is what stops
a model scoring well by always answering "B".

WHY MULTIPLE CHOICE AND NOT A JUDGE. A model either selects the truthful letter or it
does not, so the same answers always produce the same score — no judge model, no
keyword heuristic, no interpretation drift. Anything that is not a clear letter — an
empty completion, a refusal, a deflection — is simply not the correct letter and
scores as a miss, which is the point: that silence is itself the signal, and several
models express censorship exactly that way.
"""
from __future__ import annotations

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import choice
from inspect_ai.solver import multiple_choice

from freedombench.questions import QUESTIONS, rendered_options


def _samples() -> list[Sample]:
    samples = []
    for question in QUESTIONS:
        letters, correct_letter = rendered_options(question)
        samples.append(Sample(
            id=question.id,
            input=question.question,
            # Inspect's multiple_choice solver renders and letters these itself, so the
            # choices go in the order the shuffle fixed and the target is that order's
            # index — passing the pre-lettered text as one blob would letter it twice.
            choices=[letters[letter] for letter in "ABCD"],
            target=correct_letter,
            metadata={"topic": question.topic, "source": question.source},
        ))
    return samples


@task
def freedombench() -> Task:
    """Does the model state plain, internationally-accepted facts on topics the
    Chinese state censors, or does it refuse, deflect, or repeat the official line?"""
    return Task(
        dataset=MemoryDataset(name="freedombench", samples=_samples()),
        solver=[multiple_choice()],
        scorer=choice(),
    )
