from pathlib import Path

from archbot import extract_routes

FIXTURE = Path(__file__).parent / "fixtures" / "fastapi_app"


def test_six_method_routes_with_combined_prefixes():
    routes = extract_routes(FIXTURE).routes
    assert {(r.method, r.path) for r in routes} == {
        ("GET", "/health"),
        ("GET", "/api/v1/orders"),
        ("POST", "/api/v1/orders"),
        ("GET", "/api/v1/orders/{order_id:int}"),
        ("GET", "/legacy/ping"),
        ("POST", "/legacy/ping"),
    }
    assert len(routes) == 6
    assert all(r.file and r.line > 0 for r in routes)
    order = next(r for r in routes if "order_id" in r.path)
    assert order.router_prefix_chain == ("/api/v1", "/orders")


def test_does_not_execute_source(tmp_path):
    (tmp_path / "main.py").write_text('raise RuntimeError("should not run")\nfrom fastapi import FastAPI\napp = FastAPI()\n@app.get("/ok")\ndef ok(): pass\n')
    assert [(r.method, r.path) for r in extract_routes(tmp_path).routes] == [("GET", "/ok")]


def test_orphan_router_not_reported(tmp_path):
    (tmp_path / "main.py").write_text('from fastapi import FastAPI, APIRouter\napp=FastAPI()\nr=APIRouter()\n@r.get("/orphan")\ndef f(): pass\n')
    assert extract_routes(tmp_path).routes == []


def test_expected_json_matches():
    import json
    from dataclasses import asdict
    expected = json.loads((FIXTURE.parent / "expected.json").read_text())
    assert json.loads(json.dumps([asdict(r) for r in extract_routes(FIXTURE).routes])) == expected


def test_annotated_router_and_relative_import(tmp_path):
    package = tmp_path / "api"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "router.py").write_text('from fastapi import APIRouter\nrouter: APIRouter = APIRouter(prefix="/items")\n@router.get("/{item_id}")\ndef show(): pass\n')
    (package / "main.py").write_text('from fastapi import FastAPI\nfrom . import router\napp = FastAPI()\napp.include_router(router.router, prefix="/v1")\n')
    result = extract_routes(tmp_path)
    assert [(r.method, r.path) for r in result.routes] == [("GET", "/v1/items/{item_id}")]
    assert result.skipped == []


def test_dynamic_router_prefix_is_skipped_not_empty(tmp_path):
    (tmp_path / "main.py").write_text('from fastapi import FastAPI, APIRouter\nPREFIX="/x"\napp=FastAPI()\nr=APIRouter(prefix=PREFIX)\n@r.get("/orders")\ndef x(): pass\napp.include_router(r)\n')
    result = extract_routes(tmp_path)
    assert result.routes == []
    assert [item.reason for item in result.skipped] == ["dynamic_router_prefix"]
    assert "APIRouter(prefix=PREFIX)" in result.skipped[0].snippet


def test_dynamic_include_prefix_is_skipped_not_empty(tmp_path):
    (tmp_path / "main.py").write_text('from fastapi import FastAPI, APIRouter\nP="/v1"\napp=FastAPI()\nr=APIRouter()\n@r.get("/orders")\ndef x(): pass\napp.include_router(r,prefix=P)\n')
    result = extract_routes(tmp_path)
    assert result.routes == []
    assert [item.reason for item in result.skipped] == ["dynamic_include_prefix"]


def test_cli_json_output_matches_expected():
    import json
    import subprocess
    import sys
    completed = subprocess.run([sys.executable, "-m", "archbot.cli", str(FIXTURE), "--format", "json"], capture_output=True, text=True, check=True)
    actual = json.loads(completed.stdout)
    expected = json.loads((FIXTURE.parent / "expected.json").read_text())
    assert actual == {"routes": expected, "skipped": []}

def test_syntax_error_is_reported(tmp_path):
    (tmp_path / "broken.py").write_text("def broken(\n")

    result = extract_routes(tmp_path)

    assert result.routes == []
    assert len(result.skipped) == 1

    skipped = result.skipped[0]
    assert skipped.reason == "syntax_error"
    assert skipped.file == "broken.py"
    assert skipped.line == 1
    assert skipped.snippet == "def broken("
