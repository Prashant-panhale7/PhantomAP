# Contributing

Thanks for helping improve PhantomAP.

## Development setup

```bash
python -m venv .venv
. .venv/bin/activate  # Linux/macOS
python -m pip install -r requirements.txt
```

## Running tests

```bash
pytest -q
```

## Pull request expectations

- Keep Linux-first behavior and support notes explicit.
- Add or update tests for changed behavior.
- Explain any platform-specific restrictions in your PR.
- Prefer clear CLI behavior and safe fallback logic over unsupported features.
