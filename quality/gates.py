"""Normalize tool diagnostics and compare them with the tracked baseline."""

from __future__ import annotations

import ast
import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class QualityFailure(RuntimeError):
    """Raised when a quality gate finds a regression."""


@dataclass(frozen=True)
class FunctionSpan:
    qualname: str
    start: int
    end: int


def _normalized_path(path: str | Path, root: Path) -> str:
    candidate = Path(path)
    resolved = candidate.resolve()
    if resolved.is_relative_to(root.resolve()):
        candidate = resolved.relative_to(root.resolve())
    return candidate.as_posix()


def _function_spans(path: Path) -> list[FunctionSpan]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []

    spans: list[FunctionSpan] = []

    def visit(node: ast.AST, parents: tuple[str, ...]) -> None:
        next_parents = parents
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            next_parents = (*parents, node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                spans.append(
                    FunctionSpan(
                        qualname=".".join(next_parents),
                        start=node.lineno,
                        end=node.end_lineno or node.lineno,
                    )
                )
        for child in ast.iter_child_nodes(node):
            visit(child, next_parents)

    visit(tree, ())
    return spans


def enclosing_function(path: Path, line: int) -> str:
    """Return the narrowest AST function containing *line*."""

    matches = [span for span in _function_spans(path) if span.start <= line <= span.end]
    if not matches:
        return "<module>"
    return min(matches, key=lambda span: span.end - span.start).qualname


def diagnostic_counter(diagnostics: Iterable[Mapping[str, Any]], root: Path, *, tool: str) -> Counter[str]:
    """Create line-independent diagnostic fingerprints with occurrence counts."""

    counter: Counter[str] = Counter()
    for diagnostic in diagnostics:
        code, filename, line, message = _diagnostic_fields(diagnostic, tool)
        relative = _normalized_path(filename, root)
        function = enclosing_function(root / relative, line)
        counter[json.dumps([code, relative, function, message], separators=(",", ":"))] += 1
    return counter


def _diagnostic_fields(diagnostic: Mapping[str, Any], tool: str) -> tuple[str, str, int, str]:
    if tool == "ruff":
        location = diagnostic.get("location")
        line = int(location.get("row", 1)) if isinstance(location, Mapping) else 1
        return (
            str(diagnostic.get("code", "unknown")),
            str(diagnostic.get("filename", "")),
            line,
            str(diagnostic.get("message", "")),
        )
    if tool == "bandit":
        return (
            str(diagnostic.get("test_id", "unknown")),
            str(diagnostic.get("filename", "")),
            int(diagnostic.get("line_number", 1)),
            str(diagnostic.get("issue_text", "")),
        )
    raise ValueError(f"Unsupported diagnostic tool: {tool}")


def compare_counter(name: str, current: Mapping[str, int], baseline: Mapping[str, int]) -> list[str]:
    """Report only new fingerprints or increased occurrence counts."""

    failures = []
    for fingerprint, count in sorted(current.items()):
        previous = int(baseline.get(fingerprint, 0))
        if count > previous:
            failures.append(f"{name}: {fingerprint} increased from {previous} to {count}")
    return failures


def fatal_diagnostics(ruff: Iterable[Mapping[str, Any]], bandit: Iterable[Mapping[str, Any]]) -> list[str]:
    """Return diagnostics that are never eligible for baselining."""

    failures: list[str] = []
    for diagnostic in ruff:
        code = str(diagnostic.get("code") or "")
        if code.startswith("E9") or code in {"F821", "F822", "F823"}:
            failures.append(f"Ruff fatal {code}: {diagnostic.get('filename')}: {diagnostic.get('message')}")
    for diagnostic in bandit:
        if str(diagnostic.get("issue_severity") or "").upper() in {"HIGH", "CRITICAL"}:
            failures.append(
                f"Bandit fatal {diagnostic.get('test_id')}: "
                f"{diagnostic.get('filename')}: {diagnostic.get('issue_text')}"
            )
    return failures


def complexity_map(report: Mapping[str, Any], root: Path) -> dict[str, int]:
    """Flatten Radon JSON into file + qualified-function complexity keys."""

    result: dict[str, int] = {}

    def walk(path: str, blocks: Iterable[Mapping[str, Any]], parents: tuple[str, ...] = ()) -> None:
        for block in blocks:
            name = str(block.get("name") or "<unknown>")
            block_type = str(block.get("type") or "")
            next_parents = (*parents, name) if block_type == "class" else parents
            if block_type in {"function", "method"}:
                qualname = ".".join((*parents, name))
                result[f"{_normalized_path(path, root)}::{qualname}"] = int(block.get("complexity") or 0)
            walk(path, block.get("methods") or [], next_parents)
            walk(path, block.get("closures") or [], (*parents, name))

    for filename, blocks in report.items():
        if isinstance(blocks, list):
            walk(filename, blocks)
    return result


def compare_complexity(current: Mapping[str, int], baseline: Mapping[str, int], limit: int = 10) -> list[str]:
    """Prevent new complex functions and increases in existing functions."""

    failures = []
    for function, value in sorted(current.items()):
        previous = baseline.get(function)
        if previous is None and value > limit:
            failures.append(f"Radon: new {function} has complexity {value} > {limit}")
        elif previous is not None and value > previous:
            failures.append(f"Radon: {function} increased from {previous} to {value}")
    return failures


_VULTURE_LINE = re.compile(r"^(?P<file>.+?):(?P<line>\d+): (?P<message>.+?) \((?P<confidence>\d+)% confidence\)$")


def vulture_counter(output: str, root: Path) -> Counter[str]:
    """Normalize Vulture's stable text format."""

    counter: Counter[str] = Counter()
    for line in output.splitlines():
        match = _VULTURE_LINE.match(line.strip())
        if not match:
            continue
        key = json.dumps(
            [_normalized_path(match["file"], root), match["message"], int(match["confidence"])],
            separators=(",", ":"),
        )
        counter[key] += 1
    return counter


def audit_counter(report: Mapping[str, Any]) -> Counter[str]:
    """Normalize pip-audit findings by package and vulnerability id."""

    counter: Counter[str] = Counter()
    for dependency in report.get("dependencies", []):
        name = str(dependency.get("name") or "unknown").lower()
        for vulnerability in dependency.get("vulns", []):
            counter[f"{name}:{vulnerability.get('id')}"] += 1
    return counter


def raise_failures(failures: Iterable[str]) -> None:
    failures = list(failures)
    if failures:
        raise QualityFailure("Quality regressions:\n- " + "\n- ".join(failures))
