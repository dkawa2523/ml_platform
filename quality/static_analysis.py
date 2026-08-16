"""Static-analysis collection and baseline comparison."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from quality.gates import (
    QualityFailure,
    compare_counter,
    diagnostic_counter,
    fatal_diagnostics,
    raise_failures,
)
from quality.process import (
    REPORTS,
    ROOT,
    _command,
    _ensure_command_succeeded,
    _load_json_output,
    _python_module,
)

BASELINE_PATH = ROOT / "quality" / "baseline.json"
SOURCE_PATHS = ("clearml", "pkgs", "scripts", "quality", "noxfile.py")


def collect_static() -> tuple[dict[str, Any], list[str]]:
    """Collect baseline-capable diagnostics and unconditional failures."""
    ruff = _ruff()
    bandit = _bandit()
    _python_module("radon", "cc", *SOURCE_PATHS, "-j", report="radon.json")
    _run_pip_audit()
    _run_vulture()
    snapshot: dict[str, Any] = {
        "ruff": _counter_dict(diagnostic_counter(ruff, ROOT, tool="ruff")),
        "bandit": _counter_dict(diagnostic_counter(bandit, ROOT, tool="bandit")),
    }
    return snapshot, fatal_diagnostics(ruff, bandit)


def check_static(snapshot: Mapping[str, Any], baseline: Mapping[str, Any], fatal: Iterable[str]) -> None:
    failures = list(fatal)
    failures.extend(compare_counter("Ruff", snapshot["ruff"], baseline.get("ruff", {})))
    failures.extend(compare_counter("Bandit", snapshot["bandit"], baseline.get("bandit", {})))
    raise_failures(failures)


def check_changed_ruff(files: Sequence[str]) -> None:
    if not files:
        print("No changed Python files for Ruff.")
        return
    diagnostics = _ruff(files)
    failures = fatal_diagnostics(diagnostics, [])
    current = diagnostic_counter(diagnostics, ROOT, tool="ruff")
    failures.extend(compare_counter("Ruff", current, _load_baseline().get("ruff", {})))
    raise_failures(failures)


def run_pyrefly() -> None:
    result = _python_module("pyrefly", "check", "--output-format", "json", check=False, report="pyrefly.json")
    if result.returncode:
        raise QualityFailure(f"Pyrefly found type errors ({result.returncode})")


def _ruff(files: Sequence[str] | None = None) -> list[Mapping[str, Any]]:
    result = _python_module(
        "ruff", "check", *(files or (".",)), "--output-format", "json", check=False, report="ruff.json"
    )
    data = _load_json_output(result, "Ruff")
    if not isinstance(data, list):
        raise QualityFailure("Ruff JSON must be a list")
    return data


def _bandit() -> list[Mapping[str, Any]]:
    result = _python_module(
        "bandit",
        "-c",
        "pyproject.toml",
        "-r",
        "clearml",
        "pkgs",
        "scripts",
        "-q",
        "-f",
        "json",
        check=False,
        report="bandit.json",
    )
    data = _load_json_output(result, "Bandit")
    diagnostics = data.get("results", [])
    if not isinstance(diagnostics, list):
        raise QualityFailure("Bandit JSON results must be a list")
    return diagnostics


def _run_pip_audit() -> None:
    requirements = REPORTS / "audit-requirements.txt"
    _command(
        (
            "uv",
            "export",
            "--quiet",
            "--frozen",
            "--all-groups",
            "--all-extras",
            "--no-hashes",
            "--no-emit-project",
            "--no-emit-workspace",
            "--output-file",
            requirements,
        )
    )
    result = _python_module(
        "pip_audit",
        "--requirement",
        requirements,
        "--no-deps",
        "--disable-pip",
        "--format",
        "json",
        check=False,
        report="pip-audit.json",
    )
    data = _load_json_output(result, "pip-audit")
    if not isinstance(data, dict) or not isinstance(data.get("dependencies"), list):
        raise QualityFailure("pip-audit did not complete with a dependency report")
    vulnerabilities = [
        f"{dependency.get('name', 'unknown')}:{vulnerability.get('id', 'unknown')}"
        for dependency in data["dependencies"]
        for vulnerability in dependency.get("vulns", [])
    ]
    if vulnerabilities:
        raise QualityFailure("pip-audit found known vulnerabilities: " + ", ".join(sorted(vulnerabilities)))
    _ensure_command_succeeded(result)


def _run_vulture() -> None:
    result = _python_module("vulture", *SOURCE_PATHS, "--min-confidence", "80", check=False, report="vulture.txt")
    if result.stdout.strip():
        raise QualityFailure(f"Vulture found unused-code candidates:\n{result.stdout.strip()}")
    _ensure_command_succeeded(result)


def _load_baseline() -> dict[str, Any]:
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualityFailure(f"Quality baseline is missing or invalid: {BASELINE_PATH}") from exc


def _counter_dict(counter: Mapping[str, int]) -> dict[str, int]:
    return dict(sorted((key, int(value)) for key, value in counter.items()))
