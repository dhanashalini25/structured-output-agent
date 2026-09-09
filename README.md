# 01 - Structured Output Agent

> Schema-valid JSON from an LLM, every time.

**What it demonstrates:** Making LLM output reliable enough for a program to consume

**Status:** working implementation with passing tests. Built as a learning project to understand the pattern, not as a production service.

---

## Run it right now

No API key needed - every project ships with `MODEL=fake`, a deterministic
offline responder, so you can see the whole flow work before spending anything.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
python -m src.main
pytest -q
```

To use a real model, edit `.env`:

```
MODEL=gpt-4o-mini            # + OPENAI_API_KEY
MODEL=claude-3-5-haiku-latest  # + ANTHROPIC_API_KEY
MODEL=ollama/llama3.1        # free, runs locally
```

## How it works

A Pydantic model is the output contract. The model is asked for JSON matching that schema; whatever comes back goes through `coerce_json`, which strips code fences and conversational padding, then through Pydantic validation.

When validation fails, the exact error is appended to the conversation and the model is asked again - up to three attempts. Feeding back the specific error is what makes the retry succeed rather than repeat the same mistake. If all attempts fail, `strict=True` raises and `strict=False` returns a partial object with `confidence=0.0`, so the caller can always tell a good result from a salvaged one.

## What "done" means here

- A Pydantic model is the only accepted output shape
- Code fences and prose around the JSON are stripped before parsing
- Each failure feeds the exact validation error back to the model
- Retries are capped at three; the cap is enforced, not aspirational
- Every failure is logged with the raw output, error and attempt number
- Soft-fail mode returns a partial object flagged `confidence=0.0` instead of raising

Every one of those lines has a test behind it in `tests/` - `pytest -q` is the
proof, not the README.

## Layout

```
src/llm.py             provider-agnostic completion, plus offline fake mode
src/fake.py            the canned responses that make MODEL=fake work
src/logging_setup.py   structured JSON logging
src/agent.py           the pattern itself
src/main.py            CLI entrypoint
tests/                 10 tests, all passing
```

## Next steps

- Benchmark repair rate across three models and put the table here
- Add `response_format={'type': 'json_object'}` for providers that support it, and measure whether the repair loop still fires
- Try a nested schema - repair gets harder when the error is three levels deep

## Reference

https://pydantic.dev/articles/llm-intro

---

Part of a 12-project agentic AI series - [github.com/dhanashalini25](https://github.com/dhanashalini25?tab=repositories)
