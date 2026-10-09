# ARCHBOT · Evidence — PR 1 (FastAPI route extractor)

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