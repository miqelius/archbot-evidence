import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .fastapi_routes import extract_routes


def main() -> None:
    parser = argparse.ArgumentParser(description="ARCHBOT Evidence — FastAPI route extractor (v0.1)")
    parser.add_argument("backend", type=Path, help="FastAPI source root")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    result = extract_routes(args.backend)
    routes = result.routes
    if args.format == "json":
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        for route in routes:
            print(f"{route.method:7} {route.path:35} {route.file}:{route.line}")
        print(f"{len(routes)} routes found; {len(result.skipped)} skipped (static extraction only)")
        for item in result.skipped:
            print(f"SKIPPED {item.reason} {item.file}:{item.line}")


if __name__ == "__main__":
    main()