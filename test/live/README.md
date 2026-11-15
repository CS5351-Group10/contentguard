# Live tests (API-dependent)

Tests that call the real LLM API. They require credentials in the environment
(`.env`, never committed) and are **excluded from CI** by default — run locally:

```bash
pytest test/live -v
```

Rules:

- Cost-aware: each live test documents its expected token cost in the docstring.
- Live tests never run in the offline regression tier (separation per project sheet D8).
- A failing live test is triaged the same day into `docs/bug-diary.md` if significant.
