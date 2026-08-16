"""Command orchestration for the repository quality gates."""

from __future__ import annotations

import json
import os
import platform
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from quality.gates import QualityFailure, raise_failures
from quality.mutation import check_mutation, mutation_snapshot, stage_workspace
from quality.process import CommandResult as CommandResult
from quality.process import _command as _command
from quality.process import _python_module as _python_module
from quality.secrets import check_secrets as check_secrets
from quality.secrets import update_secrets_baseline as update_secrets_baseline
from quality.static_analysis import (
    check_changed_ruff as check_changed_ruff,
)
from quality.static_analysis import (
    check_static as check_static,
)
from quality.static_analysis import (
    collect_static as collect_static,
)
from quality.static_analysis import (
    run_pyrefly as run_pyrefly,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / ".quality" / "reports"
BASELINE_PATH = ROOT / "quality" / "baseline.json"
MUTATION_WORKSPACE = ROOT / ".quality" / "mutation-workspace"


def _load_baseline() -> dict[str, Any]:
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualityFailure(f"Quality baseline is missing or invalid: {BASELINE_PATH}") from exc


def _git_lines(*args: str, check: bool = True) -> list[str]:
    result = _command(("git", *args), check=check)
    if result.returncode:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def base_ref() -> str:
    """Resolve the comparison branch for local and GitHub stacked-PR runs."""

    explicit = os.environ.get("QUALITY_BASE_REF")
    if explicit:
        return explicit
    github_base = os.environ.get("GITHUB_BASE_REF")
    if github_base:
        return f"origin/{github_base}"
    preferred = "origin/agent/simplify-platform-architecture"
    if not _command(("git", "rev-parse", "--verify", preferred), check=False).returncode:
        return preferred
    return "HEAD~1"


def changed_python_files() -> list[str]:
    """Return changed, staged, committed, and untracked Python files."""

    comparison = base_ref()
    candidates = set(_git_lines("diff", "--name-only", "--diff-filter=ACMR", f"{comparison}...HEAD"))
    candidates.update(_git_lines("diff", "--name-only", "--diff-filter=ACMR"))
    candidates.update(_git_lines("diff", "--cached", "--name-only", "--diff-filter=ACMR"))
    candidates.update(_git_lines("ls-files", "--others", "--exclude-standard"))
    return sorted(path for path in candidates if path.endswith((".py", ".pyi")) and (ROOT / path).is_file())


def _test_environment(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    if extra:
        environment.update(extra)
    return environment


def run_tests(*extra_args: str) -> None:
    _python_module("pytest", *extra_args, env=_test_environment())


def run_coverage() -> dict[str, float]:
    _python_module("coverage", "erase")
    _python_module("coverage", "run", "-m", "pytest", env=_test_environment())
    _python_module("coverage", "json")
    _python_module("coverage", "xml")
    report = json.loads((REPORTS / "coverage.json").read_text(encoding="utf-8"))
    totals = report.get("totals") or {}
    return {"branch_percent": round(float(totals.get("percent_branches_covered", 0.0)), 4)}


def check_branch_coverage(current: Mapping[str, float], baseline: Mapping[str, Any]) -> None:
    expected = baseline.get("coverage")
    if not isinstance(expected, Mapping) or "branch_percent" not in expected:
        raise QualityFailure("Quality baseline is missing coverage.branch_percent; run quality-baseline explicitly")
    minimum = float(expected["branch_percent"])
    actual = float(current["branch_percent"])
    if actual + 1e-9 < minimum:
        raise QualityFailure(f"Branch coverage decreased from {minimum:.2f}% to {actual:.2f}%")


def run_diff_coverage() -> None:
    _command(
        (
            "diff-cover",
            REPORTS / "coverage.xml",
            "--compare-branch",
            base_ref(),
            "--fail-under",
            "90",
            "--format",
            f"json:{REPORTS / 'diff-coverage.json'}",
        )
    )


def run_architecture() -> None:
    _command(("lint-imports", "--config", "pyproject.toml"))


def run_smoke() -> None:
    _python_module("scripts.make_sample_data")
    _python_module(
        "scripts.local_run",
        "--task",
        "config/tasks/tabular_pipeline.yaml",
        "--profile",
        "config/profiles/local.yaml",
        "--set",
        "model.candidates=[linear,ridge,lasso,elasticnet,random_forest,extra_trees,gradient_boosting]",
    )
    _python_module(
        "scripts.local_run",
        "--task",
        "config/tasks/tabular_infer.yaml",
        "--profile",
        "config/profiles/local.yaml",
    )


def run_fast() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    files = changed_python_files()
    if files:
        _python_module("ruff", "format", *files)
    check_changed_ruff(files)
    run_pyrefly()
    run_tests()


def run_pr() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    baseline = _load_baseline()
    _python_module("ruff", "format", "--check", ".")
    snapshot, fatal = collect_static()
    check_static(snapshot, baseline, fatal)
    run_pyrefly()
    run_architecture()
    check_branch_coverage(run_coverage(), baseline)
    run_diff_coverage()
    check_secrets()
    run_smoke()


def run_mutation(*, update_baseline: bool = False) -> dict[str, dict[str, int | float]]:
    if platform.system() == "Windows":
        raise QualityFailure("mutmut 3 requires fork; run quality-nightly on GitHub Ubuntu or inside WSL")
    workspace = stage_workspace(ROOT, MUTATION_WORKSPACE)
    result = _python_module("mutmut", "run", check=False, report="mutmut-run.txt", cwd=workspace)
    if result.returncode:
        raise QualityFailure("mutmut failed to complete its mutation run")
    _python_module("mutmut", "results", "--all=true", report="mutmut-results.txt", cwd=workspace)
    current = mutation_snapshot(workspace / "mutants")
    if not update_baseline:
        check_mutation(current, _load_baseline().get("mutation", {}))
    return current


def run_nightly() -> None:
    run_pr()
    for seed in (0, 7, 42):
        run_tests("tests/test_quality_properties.py", "--hypothesis-profile", "nightly", "--hypothesis-seed", str(seed))
    run_smoke()
    run_mutation()


def update_baseline() -> None:
    """Regenerate tracked files; no other public command writes them."""

    REPORTS.mkdir(parents=True, exist_ok=True)
    snapshot, fatal = collect_static()
    raise_failures(fatal)
    snapshot["coverage"] = run_coverage()
    existing = _load_baseline() if BASELINE_PATH.exists() else {}
    if os.environ.get("QUALITY_UPDATE_MUTATION") == "1":
        snapshot["mutation"] = run_mutation(update_baseline=True)
    else:
        snapshot["mutation"] = existing.get("mutation", {})
    snapshot["schema_version"] = 1
    BASELINE_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run_pyrefly()
    update_secrets_baseline()


def run_precommit_ruff(files: Sequence[str]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    check_changed_ruff([file for file in files if Path(file).suffix in {".py", ".pyi"}])
