"""Conservative, non-executing FastAPI route extraction (v0.1).

Recognizes statically named FastAPI/APIRouter instances, route decorators,
constant-string prefixes, local imports and include_router chains.
Unknown/dynamic constructs are skipped, never executed.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from .models import Route, Skipped, RoutesResult

HTTP = {"get": ("GET",), "post": ("POST",), "put": ("PUT",),
        "patch": ("PATCH",), "delete": ("DELETE",), "head": ("HEAD",),
        "options": ("OPTIONS",)}


@dataclass
class _Module:
    name: str
    file: Path
    tree: ast.Module
    aliases: dict[str, str] = field(default_factory=dict)
    objects: dict[str, str] = field(default_factory=dict)
    prefixes: dict[str, str] = field(default_factory=dict)
    includes: list[tuple[str, str, str, int]] = field(default_factory=list)
    endpoints: list[tuple[str, str, tuple[str, ...], int]] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)


def _string(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _member(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        root = _member(node.value)
        return f"{root}.{node.attr}" if root else None
    return None


def _arg(call: ast.Call, index: int, key: str) -> ast.AST | None:
    for kw in call.keywords:
        if kw.arg == key:
            return kw.value
    return call.args[index] if len(call.args) > index else None


def _path(*parts: str) -> str:
    segments = [p.strip("/") for p in parts if p and p.strip("/")]
    return "/" + "/".join(segments) if segments else "/"


def _methods(deco: str, call: ast.Call) -> tuple[str, ...]:
    if deco in HTTP:
        return HTTP[deco]
    if deco not in {"api_route", "route"}:
        return ()
    node = _arg(call, 1, "methods")
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values = [_string(e) for e in node.elts]
        if values and all(v is not None for v in values):
            return tuple(v.upper() for v in values if v)
    return ()  # Unknown method configuration: don't invent a route.


def _module_name(root: Path, path: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _collect(root: Path) -> dict[str, _Module]:
    modules = {}
    for file in sorted(root.rglob("*.py")):
        if any(p.startswith(".") or p in {"venv", ".venv", "node_modules", "__pycache__"} for p in file.relative_to(root).parts):
            continue
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        except (UnicodeError, SyntaxError, OSError):
            continue
        name = _module_name(root, file)
        modules[name] = _Module(name, file, tree)
    return modules


def _resolve(mod: _Module, value: str) -> str:
    head, dot, tail = value.partition(".")
    return mod.aliases.get(head, f"{mod.name}.{head}") + (dot + tail if dot else "")


def _skip(mod: _Module, reason: str, node: ast.AST) -> None:
    mod.skipped.append(Skipped(reason, mod.file.as_posix(), getattr(node, "lineno", 0),
                               ast.get_source_segment(mod.file.read_text(encoding="utf-8"), node) or ""))


def _parse(mod: _Module) -> None:
    # Pass 1: imports and statically declared app/router instances.
    for stmt in mod.tree.body:
        if isinstance(stmt, ast.ImportFrom):
            # Relative imports: from .routes import router, from .routes.x import router
            base = stmt.module or ""
            if stmt.level:
                # __init__.py belongs to the package itself; other modules to their parent.
                package = mod.name.split(".") if mod.file.name == "__init__.py" else mod.name.split(".")[:-1]
                up = stmt.level - 1
                package = package[:max(0, len(package) - up)]
                base = ".".join([*package, *([base] if base else [])])
            for entry in stmt.names:
                if entry.name != "*":
                    mod.aliases[entry.asname or entry.name] = f"{base}.{entry.name}" if base else entry.name
        elif isinstance(stmt, ast.Import):
            for entry in stmt.names:
                mod.aliases[entry.asname or entry.name.split(".")[0]] = entry.name if entry.asname else entry.name.split(".")[0]
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)) and isinstance(stmt.value, ast.Call):
            constructor = _member(stmt.value.func)
            if not constructor or constructor.split(".")[-1] not in {"FastAPI", "APIRouter"}:
                continue
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                prefix_node = next((k.value for k in stmt.value.keywords if k.arg == "prefix"), None)
                prefix = _string(prefix_node) if prefix_node is not None else ""
                if prefix is None:
                    _skip(mod, "dynamic_router_prefix", stmt)
                    # Keep object identity so inclusion can be traced as an unknown subtree.
                    mod.objects[target.id] = "unknown"
                else:
                    mod.objects[target.id] = constructor.split(".")[-1]
                    mod.prefixes[target.id] = prefix
    # Pass 2: collect inclusion edges and endpoint decorators.
    for node in ast.walk(mod.tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "include_router":
            owner = _member(node.func.value)
            target_node = _arg(node, 0, "router")
            target = _member(target_node) if target_node else None
            if owner and target:
                prefix_node = next((k.value for k in node.keywords if k.arg == "prefix"), None)
                prefix = _string(prefix_node) if prefix_node is not None else ""
                if prefix is not None:
                    mod.includes.append((owner, target, prefix, node.lineno))
                else:
                    _skip(mod, "dynamic_include_prefix", node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call) or not isinstance(deco.func, ast.Attribute):
                    continue
                owner = _member(deco.func.value)
                route = _string(_arg(deco, 0, "path"))
                methods = _methods(deco.func.attr, deco)
                if owner and route is not None and methods:
                    mod.endpoints.append((owner, route, methods, node.lineno))


def extract_routes(path: Path) -> RoutesResult:
    """Find statically traceable HTTP routes without importing or running project code.

    ``path`` is the project/source root. Runtime-generated routes, dynamic
    prefixes, and imported third-party routers are intentionally unsupported.
    Returned paths are app-relative; mounted sub-apps and proxy rewrites are not modeled.
    Unresolved dynamic prefixes are reported as skipped, never treated as empty.
    """
    root = Path(path).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    modules = _collect(root)
    for mod in modules.values():
        _parse(mod)

    objects = {f"{m.name}.{name}": (m, name, kind) for m in modules.values() for name, kind in m.objects.items()}
    edges: dict[str, list[tuple[str, str]]] = {}
    endpoints: dict[str, list[tuple[_Module, str, tuple[str, ...], int]]] = {}
    for mod in modules.values():
        for owner, target, prefix, _ in mod.includes:
            edges.setdefault(_resolve(mod, owner), []).append((_resolve(mod, target), prefix))
        for owner, route, methods, line in mod.endpoints:
            endpoints.setdefault(_resolve(mod, owner), []).append((mod, route, methods, line))

    result: set[Route] = set()
    skipped = [Skipped(item.reason, Path(item.file).relative_to(root).as_posix(), item.line, item.snippet)
               for mod in modules.values() for item in mod.skipped]

    def visit(obj: str, chain: tuple[str, ...], seen: frozenset[str]) -> None:
        if obj not in objects or obj in seen:
            return
        mod, local, _ = objects[obj]
        if obj not in {k for k, (_, _, kind) in objects.items() if kind != "unknown"}:
            return
        own_prefix = mod.prefixes[local]
        current = chain + ((own_prefix,) if own_prefix else ())
        for m, route, methods, line in endpoints.get(obj, []):
            for method in methods:
                result.add(Route(method, _path(*current, route), m.file.relative_to(root).as_posix(), line, current))
        for target, include_prefix in edges.get(obj, []):
            next_chain = current + ((include_prefix,) if include_prefix else ())
            visit(target, next_chain, seen | {obj})

    # Only routes reachable from FastAPI roots are active; orphan routers are excluded.
    for obj, (_, _, kind) in objects.items():
        if kind == "FastAPI":
            visit(obj, (), frozenset())
    return RoutesResult(sorted(result, key=lambda r: (r.path, r.method, r.file, r.line)),
                        sorted(skipped, key=lambda item: (item.file, item.line, item.reason)))