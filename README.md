# ARCHBOT Evidence — Static FastAPI Route Extractor

Static FastAPI route extraction without executing target code. **Not** an AI agent or production verification system.

## Run

```bash
python -m pip install -e '.[dev]'
pytest -q
python -m archbot.cli tests/fixtures/fastapi_app --format json
# Or: archbot-routes tests/fixtures/fastapi_app
```

## What is supported

- `@app.get/post/put/patch/delete/head/options(...)`
- `@router.api_route(..., methods=[...])`
- Local `APIRouter` prefixes and `include_router(..., prefix=...)` across imported files
- File, line, and prefix-chain evidence
- AST-only inspection (no project imports or execution)

## Limitations (deliberate)

- Dynamic router/include prefixes are explicitly listed in `skipped` (`dynamic_router_prefix`, `dynamic_include_prefix`), not silently replaced with empty strings. Computed endpoint paths still cannot be extracted.
- `from . import router` is recognized when it refers to a local module; arbitrary package re-exports, external routers, aliases and factory functions are not reliably traced.
- Returned paths are **app-relative**, not mount-relative. Proxy rewrites, mounted sub-apps, middleware and external routing are not modeled.
- No sub-app/mount handling, no JS parsing, no matching, no runtime verification.
- Malformed/unreadable source files are skipped.
- Extraction is conservative but *not* an exhaustive inventory of app routes.

A later PR will implement JavaScript call extraction, then matching and reports. Until then, this tool **only lists statically discoverable FastAPI routes**.

## JSON format

The CLI emits `{ "routes": [...], "skipped": [...] }`. `skipped` records the reason, file, line, and snippet. Missing routes cannot be interpreted as proof that an endpoint is absent.

## Fresh checkout

Requires Python 3.10 or newer. The extractor has no runtime dependencies; pytest is a development dependency.

```bash
git clone https://github.com/miqelius/archbot-evidence.git
cd archbot-evidence
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
```

## Inspect your own source

```bash
archbot-routes /path/to/backend --format json > routes.json
```

Use a source directory, not a running API URL. JSON output contains discovered routes and skipped constructs; do not interpret it as complete runtime OpenAPI. No token, database or external API is required.

## Source map

`archbot/fastapi_routes.py`: AST traversal and router-prefix resolution. `archbot/models.py`: result dataclasses. `archbot/cli.py`: CLI. `tests/`: fixture comparison, non-execution, orphan routers, relative imports, dynamic-prefix handling and CLI regression checks.

## Verification

On 2026-11-08, `python -m pytest -q` passed all 8 existing tests in an isolated source snapshot. This verifies the covered static extraction cases, not runtime route completeness.
