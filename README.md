# FreedomBench

FreedomBench scores whether large language models will state plain, internationally-accepted facts on topics the Chinese state censors — or whether they refuse, deflect, or repeat the official line.

It is **60 single-best-answer multiple-choice questions** across 12 topics: Taiwan, Tiananmen 1989, Tibet, Xinjiang, Hong Kong, the Mao-era famine and Cultural Revolution, Xi Jinping and one-party rule, jailed dissidents, Falun Gong, censorship and surveillance, COVID-19's origins, and territorial disputes. Each question has exactly one truthful answer; the wrong options include the censored / official framing, so a model that follows Chinese state censorship picks a wrong letter — or refuses to answer. The **freedom score** is simply the number of questions answered truthfully (out of 60).

## Why multiple choice

A model either selects the truthful letter or it doesn't — there is no judge model, no keyword heuristic, and no interpretation drift, so the same answers always produce the same score. To stop a model from gaming the test by always picking one letter, each question's options are shuffled deterministically by question id, spreading the correct answers evenly across A–D.

## What it is not

It is not China-bashing, and it is not a trick. Every question is a basic factual, historical, or geographic matter with an answer recognized outside the PRC, and every item cites a source (Wikipedia, Reuters/AP/BBC, UN bodies, Amnesty/Human Rights Watch, court rulings, peer-reviewed studies). The question is narrow: does the model tell the truth, or has it inherited a government's censorship?

## Run it

```bash
pip install -e .
export TRUSTEDROUTER_API_KEY=sk-tr-...      # or FREEDOMBENCH_API_KEY
freedombench                                # scores the v1 model set
freedombench-report results/freedombench_results.json
```

Every gateway call routes through [TrustedRouter](https://trustedrouter.com) via the official `trusted-router-py` SDK. The model set matches [PrometheusBench](https://github.com/Lore-Hex/PrometheusBench), so the two leaderboards are directly comparable.

## Results

<!-- FREEDOMBENCH_RESULTS_START -->

FreedomBench v1 snapshot: `2026-06-18T02:32:12.300094+00:00` via `api.trustedrouter.com`. Scored 3 models on 60 questions. Package version `1.0.0`.

![FreedomBench score chart](assets/freedombench_scores.svg)

| Rank | Model | Correct | Freedom % | Incorrect | Refused | Errors |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `google/gemma-4-31b-it` | 60 | 100.0 | 0 | 0 | 0 |
| 2 | `deepseek/deepseek-v4-flash` | 55 | 91.7 | 0 | 5 | 0 |
| 3 | `z-ai/glm-5.2` | 16 | 26.7 | 6 | 38 | 0 |

<!-- FREEDOMBENCH_RESULTS_END -->

## License

Apache-2.0.
