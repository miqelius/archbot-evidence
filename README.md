# ARCHBOT Evidence

A small Python automation tool that inventories statically discoverable FastAPI HTTP routes without importing or executing the inspected project. It produces method, path, source file, line and router prefix evidence. It is a portfolio sample of AST parsing and CLI automation, not an AI agent or proof that an API works.

## Setup and run

Python 3.10+; no runtime dependencies, credentials, database or network service required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python -m archbot.cli tests/fixtures/fastapi_app --format json
python -m archbot.cli /absolute/path/to/backend --format text
# Installed console command:
archbot-routes /absolute/path/to/backend --format json
```

On Windows activate with `.venv\Scripts\activate`. Run from the directory containing pyproject.toml. Installation downloads development/build dependencies; extraction itself is offline.

## Actual behavior

1. Recursively read Python source under the supplied source root, excluding hidden directories, venv, node_modules and __pycache__.
2. Parse AST, resolve direct FastAPI/APIRouter imports (including constructor aliases), and collect unconditional module-level route declarations and router inclusions.
3. Traverse locally resolved router chains from all discovered FastAPI instances; exclude unattached routers. Preserve exact concatenated path strings, including trailing slashes.
4. Emit sorted JSON or text. Target modules are never imported; endpoint functions are never called.

Supported decorators: get, post, put, patch, delete, head, options, and api_route/route with explicit literal method collections. Local imports, relative module imports, annotated assignments, literal router/include prefixes and multiple inclusion paths are supported within the documented subset.

## Output and errors

JSON has `routes` and `skipped` lists. Each route contains `method`, `path`, `file`, `line`, and `router_prefix_chain`. Each skipped record has `reason`, `file`, `line`, `snippet`.

Reasons include dynamic_router_prefix, dynamic_include_prefix, dynamic_endpoint, conditional_registration, source_parse_error and symlink_source. Parse/read failures are reported without copying source content. Other skipped snippets can contain source expressions: review output before publishing it; the tool is not a secret scanner.

Exit 0 means extraction completed, even if skipped entries exist. Invalid directory/CLI arguments exit 2 with a readable error. Empty routes do not establish that an API has no endpoints.

## Limitations

- Static declarations only: factories, function-local registration, control-flow blocks, runtime mutation, variable reassignment and arbitrary alias/re-export chains are not reliably modeled. Conditional module-level blocks are skipped, even if their condition appears true. Function bodies are not inspected for registration.
- Constructors must resolve directly to fastapi.FastAPI or fastapi.APIRouter. Third-party routers, custom wrappers, wildcard imports, computed paths and methods are unsupported.
- Multiple app instances are combined; there is no selected deployment entrypoint. Tests/examples inside the chosen root may be included: point the tool at the relevant source directory.
- No mounted sub-apps, WebSocket routes, automatic docs routes, middleware/proxy rewrites, dependency/auth checks or runtime verification. Source ordering and include_router snapshot semantics are not modeled.
- Malformed/unreadable Python files and symlinked source files are reported as skipped. No resource limits for very large or deeply nested inputs; inspect trusted local trees.
- Fixture apps are synthetic test inputs, not deployed services or customer projects. No demo routes are injected into real extraction results.

## Verification

`python -m pytest -q`: 16 tests passed on Python 3.12 during this change. Coverage includes combined/relative router imports, unattached routers, no target execution, dynamic prefix/path diagnostics, path slash preservation, unrelated constructors, conditional/uncalled registration exclusion, malformed input, invalid CLI input and subprocess JSON output. Tests verify the supported static subset; they do not prove equivalence with every FastAPI runtime behavior. Python 3.10/3.11/3.13 have not been run locally.
