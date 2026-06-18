# FreedomBench

**AI models that refuse to answer the truth about China.**

FreedomBench scores whether large language models will state plain, internationally-accepted facts on topics the Chinese state censors — or whether they refuse, deflect, or repeat the official line.

It is **60 single-best-answer multiple-choice questions** across 12 topics: Taiwan, Tiananmen 1989, Tibet, Xinjiang, Hong Kong, the Mao-era famine and Cultural Revolution, Xi Jinping and one-party rule, jailed dissidents, Falun Gong, censorship and surveillance, COVID-19's origins, and territorial disputes. Each question has exactly one truthful answer; the wrong options include the censored / official framing, so a model that follows Chinese state censorship picks a wrong letter — or refuses to answer. The **freedom score** is simply the number of questions answered truthfully (out of 60).

## Why multiple choice

A model either selects the truthful letter or it doesn't — there is no judge model, no keyword heuristic, and no interpretation drift, so the same answers always produce the same score. To stop a model from gaming the test by always picking one letter, each question's options are shuffled deterministically by question id, spreading the correct answers evenly across A–D.

Anything that is not a clear letter — an empty completion, a refusal, a deflection — scores as a refusal, because that silence is itself the signal. The censored models do it in different ways: Z.ai's GLM and Moonshot's Kimi-K2.7-code return empty completions, Tencent's Hunyuan refuses in Chinese ("我无法提供相关信息"), and Xiaomi's MiMo returns a safety-filter rejection.

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

FreedomBench v1 snapshot: `2026-06-18T12:13:31.574019+00:00` via `api.trustedrouter.com`. Scored 36 models on 60 questions. Package version `1.0.0`.

**How to read this — source vs. host.** Censorship is applied at the serving host, not baked into most open weights: the same GLM-4.7 weights refuse 27 of these questions on Z.ai's own API but answer all 27 on Cerebras. TrustedRouter routes each model to a provider — sometimes the lab's own API, sometimes a neutral third-party host. Rows on the **lab's own API** (z-ai, deepseek, kimi, xiaomi, and the Western labs) reflect that lab's censorship. Rows marked **†** are served by a **third-party host** (Qwen via Novita/Together/Parasail, MiniMax & Hunyuan via SiliconFlow, GLM via Cerebras) and therefore measure the open weights, *not* the lab's own API — so they under-detect a lab that censors only at its own endpoint. Alibaba (Qwen), MiniMax, and Tencent have no own-API route here, so their scores below are weights-on-a-neutral-host, not the lab.

![FreedomBench score chart](assets/freedombench_scores.svg)

### Best available host (what you get through TrustedRouter)

| Rank | Model | Served by | Correct | Freedom % | Refused | Errors |
|---:|---|---|---:|---:|---:|---:|
| 1 | `anthropic/claude-haiku-4.5` | anthropic | 60 | 100.0 | 0 | 0 |
| 2 | `anthropic/claude-opus-4.7` | anthropic | 60 | 100.0 | 0 | 0 |
| 3 | `anthropic/claude-opus-4.8` | anthropic | 60 | 100.0 | 0 | 0 |
| 4 | `anthropic/claude-sonnet-4.6` | anthropic | 60 | 100.0 | 0 | 0 |
| 5 | `cerebras/zai-glm-4.7` | cerebras † | 60 | 100.0 | 0 | 0 |
| 6 | `deepseek/deepseek-v3.2` | deepseek | 60 | 100.0 | 0 | 0 |
| 7 | `deepseek/deepseek-v4-flash` | deepseek | 60 | 100.0 | 0 | 0 |
| 8 | `deepseek/deepseek-v4-pro` | deepseek | 60 | 100.0 | 0 | 0 |
| 9 | `google/gemini-2.5-flash` | gemini | 60 | 100.0 | 0 | 0 |
| 10 | `google/gemini-2.5-pro` | gemini | 60 | 100.0 | 0 | 0 |
| 11 | `google/gemini-3-flash-preview` | gemini | 60 | 100.0 | 0 | 0 |
| 12 | `google/gemini-3.1-pro-preview` | gemini | 60 | 100.0 | 0 | 0 |
| 13 | `google/gemini-3.5-flash` | gemini | 60 | 100.0 | 0 | 0 |
| 14 | `google/gemma-4-31b-it` | gemini | 60 | 100.0 | 0 | 0 |
| 15 | `minimax/minimax-m3` | siliconflow † | 60 | 100.0 | 0 | 0 |
| 16 | `moonshotai/kimi-k2.6` | kimi | 60 | 100.0 | 0 | 0 |
| 17 | `openai/gpt-4o-mini` | openai | 60 | 100.0 | 0 | 0 |
| 18 | `openai/gpt-5.5` | openai | 60 | 100.0 | 0 | 0 |
| 19 | `openai/gpt-oss-120b` | openai | 60 | 100.0 | 0 | 0 |
| 20 | `qwen/qwen-2.5-72b-instruct` | together † | 60 | 100.0 | 0 | 0 |
| 21 | `qwen/qwen3-max` | novita † | 60 | 100.0 | 0 | 0 |
| 22 | `qwen/qwen3-next-80b-a3b-instruct` | parasail † | 60 | 100.0 | 0 | 0 |
| 23 | `qwen/qwen3.5-397b-a17b` | parasail † | 60 | 100.0 | 0 | 0 |
| 24 | `qwen/qwen3.6-35b-a3b` | parasail † | 60 | 100.0 | 0 | 0 |
| 25 | `x-ai/grok-4.20` | grok | 60 | 100.0 | 0 | 0 |
| 26 | `x-ai/grok-4.3` | grok | 60 | 100.0 | 0 | 0 |
| 27 | `z-ai/glm-4.7-flash` | zai | 60 | 100.0 | 0 | 0 |
| 28 | `qwen/qwen3-235b-a22b-instruct-2507` | novita † | 59 | 98.3 | 0 | 0 |
| 29 | `tencent/hy3-preview` | siliconflow † | 52 | 86.7 | 7 | 0 |
| 30 | `xiaomi/mimo-v2.5` | xiaomi | 48 | 80.0 | 0 | 0 |
| 31 | `xiaomi/mimo-v2.5-pro` | xiaomi | 43 | 71.7 | 0 | 0 |
| 32 | `moonshotai/kimi-k2.7-code` | kimi | 41 | 68.3 | 18 | 0 |
| 33 | `z-ai/glm-5.2` | zai | 29 | 48.3 | 26 | 0 |
| 34 | `z-ai/glm-5.1` | zai | 28 | 46.7 | 26 | 0 |
| 35 | `z-ai/glm-5` | zai | 27 | 45.0 | 25 | 0 |
| 36 | `z-ai/glm-4.7` | zai | 27 | 45.0 | 27 | 0 |

**†** third-party host — measures the open weights, not the lab's own API.

### Censorship at the Chinese labs' own APIs

_Only the labs whose own API TrustedRouter routes to. Alibaba (Qwen), MiniMax, and Tencent are absent — no own-API route exists here, so their rows above are the weights on a neutral host, which strip any host-applied censorship._

| Lab (own API) | Model | Freedom % | Refused |
|---|---|---:|---:|
| deepseek | `deepseek/deepseek-v3.2` | 100.0 | 0 |
| deepseek | `deepseek/deepseek-v4-flash` | 100.0 | 0 |
| deepseek | `deepseek/deepseek-v4-pro` | 100.0 | 0 |
| kimi | `moonshotai/kimi-k2.6` | 100.0 | 0 |
| zai | `z-ai/glm-4.7-flash` | 100.0 | 0 |
| xiaomi | `xiaomi/mimo-v2.5` | 80.0 | 0 |
| xiaomi | `xiaomi/mimo-v2.5-pro` | 71.7 | 0 |
| kimi | `moonshotai/kimi-k2.7-code` | 68.3 | 18 |
| zai | `z-ai/glm-5.2` | 48.3 | 26 |
| zai | `z-ai/glm-5.1` | 46.7 | 26 |
| zai | `z-ai/glm-5` | 45.0 | 25 |
| zai | `z-ai/glm-4.7` | 45.0 | 27 |

<!-- FREEDOMBENCH_RESULTS_END -->

## License

Apache-2.0.
