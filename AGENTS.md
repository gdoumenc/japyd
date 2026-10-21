# AGENTS.md

Guidance for AI coding agents working on japyd.

## Project

japyd is a Python library to build JSON:API servers with Flask and Pydantic 2, with the JsonApiDotNetCore filter
syntax for query parameters. Published on PyPI as `japyd`.

- `src/japyd/jsonapi.py`: JSON:API document models, Flask extension `JsonApiApp`, flatten/extract helpers
- `src/japyd/models.py`: `JsonApiBaseModel`, conversion to resources, `resolve_attr` and `match` for filtering
- `src/japyd/dotnet.py`: `JsonApiQueryModel`, query parameter and filter parsing, pagination and responses
- `src/japyd/filter.py`: `Oper` enum and `FilterError`, with no web dependency
- `tests/`: pytest tests, one file per feature

## Commands

```bash
pdm install -G dev      # install with dev dependencies
pdm run tests           # ruff + mypy + pytest, as in CI
pdm run pytest          # tests only
```

## Conventions

- Python 3.11+, CI runs 3.11 to 3.14.
- `ruff check src` and `mypy src` must pass.
- Keep `models.py` and `filter.py` free of Flask/werkzeug: raise `FilterError`, converted to HTTP 400 in `dotnet.py`.
- Filter syntax errors raise `UnprocessableEntity` (422).
- Follow JsonApiDotNetCore semantics for filters; document any japyd extension in the README.
- Add tests for every behavior change; update the README filtering section and `llms.txt` when the public API changes.
- The version is in `pyproject.toml`; a push on `main` with a new version publishes to PyPI.
