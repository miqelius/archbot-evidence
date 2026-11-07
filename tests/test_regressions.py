import json
import subprocess
import sys

from archbot import extract_routes


def source(tmp_path, text):
    (tmp_path / "main.py").write_text(text)
    return extract_routes(tmp_path)


def test_trailing_slashes_are_distinct(tmp_path):
    result = source(tmp_path, 'from fastapi import FastAPI\napp=FastAPI()\n@app.get("/items/")\ndef a(): pass\n@app.get("/items")\ndef b(): pass\n')
    assert {r.path for r in result.routes} == {"/items", "/items/"}


def test_import_alias_constructor(tmp_path):
    result = source(tmp_path, 'from fastapi import FastAPI as API\napp=API()\n@app.get("/ok")\ndef a(): pass\n')
    assert [r.path for r in result.routes] == ["/ok"]


def test_unrelated_constructor_is_not_fastapi(tmp_path):
    result = source(tmp_path, 'from other import FastAPI\napp=FastAPI()\n@app.get("/fake")\ndef a(): pass\n')
    assert result.routes == []


def test_uncalled_factory_and_false_branch_are_not_registered(tmp_path):
    result = source(tmp_path, 'from fastapi import FastAPI, APIRouter\napp=FastAPI()\nr=APIRouter()\n@r.get("/no")\ndef a(): pass\ndef setup():\n app.include_router(r)\nif False:\n app.include_router(r)\n')
    assert result.routes == []
    assert [s.reason for s in result.skipped] == ["conditional_registration"]


def test_bad_source_is_reported_without_source_content(tmp_path):
    result = source(tmp_path, 'def broken(')
    assert result.routes == []
    assert result.skipped[0].reason == "source_parse_error"
    assert result.skipped[0].snippet == ""


def test_dynamic_endpoint_is_reported(tmp_path):
    result = source(tmp_path, 'from fastapi import FastAPI\napp=FastAPI()\nP="/x"\n@app.get(P)\ndef a(): pass\n')
    assert result.routes == []
    assert result.skipped[0].reason == "dynamic_endpoint"


def test_cli_invalid_directory(tmp_path):
    run = subprocess.run([sys.executable, "-m", "archbot.cli", str(tmp_path / "absent")], capture_output=True, text=True)
    assert run.returncode == 2
    assert "Not a directory" in run.stderr
    assert "Traceback" not in run.stderr


def test_cli_real_input_to_json(tmp_path):
    source(tmp_path, 'from fastapi import FastAPI\napp=FastAPI()\n@app.post("/jobs/")\ndef submit(): pass\n')
    run = subprocess.run([sys.executable, "-m", "archbot.cli", str(tmp_path), "--format", "json"], capture_output=True, text=True, check=True)
    result = json.loads(run.stdout)
    assert result["routes"][0]["path"] == "/jobs/"
    assert result["routes"][0]["method"] == "POST"
    assert result["skipped"] == []
