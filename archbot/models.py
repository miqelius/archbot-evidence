from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Route:
    method: str
    path: str
    file: str
    line: int
    router_prefix_chain: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Skipped:
    reason: str
    file: str
    line: int
    snippet: str


@dataclass(frozen=True, slots=True)
class RoutesResult:
    routes: list[Route]
    skipped: list[Skipped]