"""Command orchestration for the repository quality gates."""

from __future__ import annotations

import asyncio
import json
import os
import platform
import shutil
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quality.gates import (
    QualityFailure,
    audit_counter,
    compare_complexity,
    compare_counter,
    complexity_map,
    diagnostic_counter,
    fatal_diagnostics,
    raise_failures,
    vulture_counter,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / ".quality" / "reports"
BASELINE_PATH = ROOT / "quality" / "baseline.json"
PYREFLY_BASELINE_PATH = ROOT / "quality" / "pyrefly-baseline.json"
SECRETS_BASELINE_PATH = ROOT / ".secrets.baseline"
MUTATION_WORKSPACE = ROOT / ".quality" / "mutation-workspace"
SOURCE_PATHS = ("clearml", "pkgs", "scripts", "quality", "noxfile.py")
SECRETS_EXCLUDE = (
    r"(?:^|[\\/])(?:\.git|\.venv(?:-[^\\/]+)?|\.quality|\.import_linter_cache|\.mypy_cache|"
    r"\.ruff_cache|\.uv-cache(?:-codex)?|\.pytest_cache|\.hypothesis|mutants|outputs|data)(?:[\\/]|$)"
    r"|(?:^|[\\/])\.secrets\.baseline$"
)
BANDIT_RATIONALE = {
    "B301": "Joblib/pickle loading is limited to model artifacts selected by the operator; untrusted uploads are out of scope.",
    "B403": "Pickle is retained only for the established model artifact format and is covered by artifact compatibility tests.",
    "B404": "Git metadata probes use fixed argument vectors without a shell and never execute configuration-provided commands.",
    "B603": "Subprocess calls use fixed executables and argument arrays with shell execution disabled.",
    "B607": "Git is intentionally resolved from the Agent or developer PATH for portable source revision discovery.",
}
INITIAL_MEASUREMENTS = {
    "pytest_passed": 188,
    "branch_coverage_percent": 81,
    "ruff_diagnostics": 184,
    "pyrefly_errors": 49,
    "complexity_over_10": 8,
    "bandit_findings": 11,
    "dependency_vulnerabilities": 21,
    "vulture_candidates": 0,
}
_MUTATION_STATUS_BY_EXIT_CODE = {
    None: "not_checked",
    -11: "segfault",
    -9: "segfault",
    -24: "timeout",
    0: "survived",
    1: "killed",
    2: "interrupted",
    3: "killed",
    5: "untested",
    24: "timeout",
    33: "untested",
    34: "skipped",
    35: "suspicious",
    36: "timeout",
    37: "killed",
    152: "timeout",
    255: "timeout",
}


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


async def _execute(command: tuple[str, ...], command_env: Mapping[str, str], command_cwd: Path) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=command_cwd,
        env=command_env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    returncode = process.returncode
    if returncode is None:
        raise QualityFailure(f"Command did not terminate: {' '.join(command)}")
    return (
        returncode,
        stdout_bytes.decode("utf-8", errors="replace"),
        stderr_bytes.decode("utf-8", errors="replace"),
    )


def _emit_command_output(stdout: str, stderr: str, report: str | None) -> None:
    if stdout and not (report and report.endswith(".json")):
        _print_compatible(stdout, sys.stdout)
    if stderr:
        _print_compatible(stderr, sys.stderr)
    if report:
        (REPORTS / report).write_text(stdout, encoding="utf-8")


def _print_compatible(output: str, stream: Any) -> None:
    encoding = stream.encoding or "utf-8"
    compatible = output.encode(encoding, errors="replace").decode(encoding)
    print(compatible, end="" if compatible.endswith("\n") else "\n", file=stream)


def _ensure_command_succeeded(result: CommandResult) -> None:
    if result.returncode:
        raise QualityFailure(f"Command failed ({result.returncode}): {' '.join(result.args)}")


def _command(
    args: Sequence[str | Path],
    *,
    check: bool = True,
    env: Mapping[str, str] | None = None,
    report: str | None = None,
    cwd: Path = ROOT,
) -> CommandResult:
    command = tuple(str(arg) for arg in args)
    print(f"+ {' '.join(command)}", flush=True)
    command_env = os.environ.copy()
    if env:
        command_env.update(env)
    returncode, stdout, stderr = asyncio.run(_execute(command, command_env, cwd))
    _emit_command_output(stdout, stderr, report)
    result = CommandResult(command, returncode, stdout, stderr)
    if check:
        _ensure_command_succeeded(result)
    return result


def _python_module(module: str, *args: str | Path, **kwargs: Any) -> CommandResult:
    return _command((sys.executable, "-m", module, *args), **kwargs)


def _load_json_output(result: CommandResult, name: str) -> Any:
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise QualityFailure(f"{name} did not produce valid JSON: {exc}") from exc


def _load_baseline() -> dict[str, Any]:
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualityFailure(f"Quality baseline is missing or invalid: {BASELINE_PATH}") from exc


def _counter_dict(counter: Mapping[str, int]) -> dict[str, int]:
    return dict(sorted((key, int(value)) for key, value in counter.items()))


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


def _ruff(files: Sequence[str] | None = None) -> list[Mapping[str, Any]]:
    targets = tuple(files or (".",))
    result = _python_module("ruff", "check", *targets, "--output-format", "json", check=False, report="ruff.json")
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


def _radon() -> dict[str, Any]:
    result = _python_module("radon", "cc", *SOURCE_PATHS, "-j", check=False, report="radon.json")
    data = _load_json_output(result, "Radon")
    if not isinstance(data, dict):
        raise QualityFailure("Radon JSON must be an object")
    return data


def _vulture() -> Counter[str]:
    result = _python_module("vulture", *SOURCE_PATHS, "--min-confidence", "80", check=False, report="vulture.txt")
    return vulture_counter(result.stdout, ROOT)


def _pip_audit() -> Counter[str]:
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
    return audit_counter(data)


def collect_static() -> tuple[dict[str, Any], list[str]]:
    """Collect baseline-capable diagnostics and unconditional failures."""

    ruff = _ruff()
    bandit = _bandit()
    radon = _radon()
    snapshot: dict[str, Any] = {
        "ruff": _counter_dict(diagnostic_counter(ruff, ROOT, tool="ruff")),
        "bandit": _counter_dict(diagnostic_counter(bandit, ROOT, tool="bandit")),
        "complexity": dict(sorted(complexity_map(radon, ROOT).items())),
        "pip_audit": _counter_dict(_pip_audit()),
        "vulture": _counter_dict(_vulture()),
    }
    return snapshot, fatal_diagnostics(ruff, bandit)


def check_static(snapshot: Mapping[str, Any], baseline: Mapping[str, Any], fatal: Iterable[str]) -> None:
    failures = list(fatal)
    failures.extend(compare_counter("Ruff", snapshot["ruff"], baseline.get("ruff", {})))
    failures.extend(compare_counter("Bandit", snapshot["bandit"], baseline.get("bandit", {})))
    failures.extend(compare_complexity(snapshot["complexity"], baseline.get("complexity", {})))
    failures.extend(compare_counter("pip-audit", snapshot["pip_audit"], baseline.get("pip_audit", {})))
    failures.extend(compare_counter("Vulture", snapshot["vulture"], baseline.get("vulture", {})))
    raise_failures(failures)


def check_changed_ruff(files: Sequence[str]) -> None:
    if not files:
        print("No changed Python files for Ruff.")
        return
    diagnostics = _ruff(files)
    fatal = fatal_diagnostics(diagnostics, [])
    current = diagnostic_counter(diagnostics, ROOT, tool="ruff")
    failures = [*fatal, *compare_counter("Ruff", current, _load_baseline().get("ruff", {}))]
    raise_failures(failures)


def run_pyrefly(*, update_baseline: bool = False) -> None:
    args: list[str | Path] = ["check", "--output-format", "json"]
    if update_baseline:
        args.extend(("--baseline", PYREFLY_BASELINE_PATH, "--update-baseline"))
    result = _python_module("pyrefly", *args, check=False, report="pyrefly.json")
    if result.returncode:
        raise QualityFailure(f"Pyrefly found type errors ({result.returncode})")


def _test_environment(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    if extra:
        environment.update(extra)
    return environment


def run_tests(*extra_args: str) -> None:
    _python_module("pytest", *extra_args, env=_test_environment())


def run_coverage() -> dict[str, Any]:
    _python_module("coverage", "erase")
    _python_module("coverage", "run", "-m", "pytest", env=_test_environment())
    _python_module("coverage", "json")
    _python_module("coverage", "xml")
    return json.loads((REPORTS / "coverage.json").read_text(encoding="utf-8"))


def _coverage_percent(report: Mapping[str, Any]) -> float:
    try:
        return float(report["totals"]["percent_covered"])
    except (KeyError, TypeError, ValueError) as exc:
        raise QualityFailure("coverage.json does not contain totals.percent_covered") from exc


def check_coverage(report: Mapping[str, Any], baseline: Mapping[str, Any]) -> None:
    current = _coverage_percent(report)
    required = float(baseline.get("coverage", {}).get("percent", 81.0))
    if current + 1e-9 < required:
        raise QualityFailure(f"Branch coverage dropped from {required:.2f}% to {current:.2f}%")


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


def _scan_secrets() -> dict[str, Any]:
    result = _command(
        ("detect-secrets", "scan", "--all-files", "--exclude-files", SECRETS_EXCLUDE),
        check=False,
        report="detect-secrets.json",
    )
    data = _load_json_output(result, "detect-secrets")
    if not isinstance(data, dict):
        raise QualityFailure("detect-secrets JSON must be an object")
    return data


def _secret_counter(report: Mapping[str, Any]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for filename, findings in report.get("results", {}).items():
        for finding in findings:
            key = json.dumps(
                [Path(filename).as_posix(), finding.get("type"), finding.get("hashed_secret")],
                separators=(",", ":"),
            )
            counter[key] += 1
    return counter


def check_secrets() -> None:
    try:
        baseline = json.loads(SECRETS_BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualityFailure("detect-secrets baseline is missing or invalid") from exc
    failures = compare_counter("detect-secrets", _secret_counter(_scan_secrets()), _secret_counter(baseline))
    raise_failures(failures)


def update_secrets_baseline() -> None:
    parsed = _scan_secrets()
    SECRETS_BASELINE_PATH.write_text(json.dumps(parsed, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    coverage_report = run_coverage()
    check_coverage(coverage_report, baseline)
    run_diff_coverage()
    check_secrets()
    run_smoke()


def _mutation_snapshot(mutants_root: Path | None = None) -> dict[str, dict[str, int | float]]:
    root = mutants_root or ROOT / "mutants"
    snapshots: dict[str, dict[str, int | float]] = {}
    for metadata_path in sorted(root.rglob("*.py.meta")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise QualityFailure(f"Invalid mutmut metadata: {metadata_path}") from exc
        codes = metadata.get("exit_code_by_key", {}).values()
        statuses = Counter(_MUTATION_STATUS_BY_EXIT_CODE.get(code, "suspicious") for code in codes)
        total = sum(statuses.values())
        killed = statuses["killed"]
        module_path = metadata_path.relative_to(root).with_suffix("")
        if module_path.parts[:1] == ("src",):
            module_path = Path(*module_path.parts[1:])
        module = module_path.as_posix()
        snapshots[module] = {
            "killed": killed,
            "survived": statuses["survived"],
            "untested": statuses["untested"],
            "incomplete": total - killed - statuses["survived"] - statuses["untested"],
            "total": total,
            "kill_rate": round(100.0 * killed / total, 4) if total else 0.0,
        }
    if not snapshots:
        raise QualityFailure("mutmut produced no module metadata")
    return snapshots


def check_mutation(
    current: Mapping[str, Mapping[str, int | float]],
    baseline: Mapping[str, Mapping[str, int | float]],
) -> None:
    failures: list[str] = []
    for module, stats in current.items():
        previous = baseline.get(module)
        if previous is None:
            failures.append(f"mutmut: {module} has no baseline")
            continue
        if int(stats["incomplete"]):
            failures.append(f"mutmut: {module} has {stats['incomplete']} incomplete mutants")
        for field in ("survived", "untested"):
            if int(stats[field]) > int(previous[field]):
                failures.append(f"mutmut: {module} {field} increased from {previous[field]} to {stats[field]}")
        if float(stats["kill_rate"]) + 1e-9 < float(previous["kill_rate"]):
            failures.append(
                f"mutmut: {module} kill rate dropped from {previous['kill_rate']}% to {stats['kill_rate']}%"
            )
    for missing in sorted(set(baseline) - set(current)):
        failures.append(f"mutmut: baseline module was not evaluated: {missing}")
    raise_failures(failures)


def _stage_mutation_workspace() -> Path:
    MUTATION_WORKSPACE.mkdir(parents=True, exist_ok=True)
    for name in ("src", "tests", "config", "clearml"):
        target = MUTATION_WORKSPACE / name
        if target.exists():
            shutil.rmtree(target)
    source = MUTATION_WORKSPACE / "src"
    source.mkdir()
    shutil.copytree(ROOT / "pkgs/core/src/ml_platform_core", source / "ml_platform_core")
    shutil.copytree(ROOT / "pkgs/tabular/src/ml_platform_tabular", source / "ml_platform_tabular")
    shutil.copytree(ROOT / "tests", MUTATION_WORKSPACE / "tests")
    shutil.copytree(ROOT / "config", MUTATION_WORKSPACE / "config")
    shutil.copytree(ROOT / "clearml", MUTATION_WORKSPACE / "clearml")
    shutil.copy2(ROOT / "pyproject.toml", MUTATION_WORKSPACE / "pyproject.toml")
    shutil.copy2(ROOT / "uv.lock", MUTATION_WORKSPACE / "uv.lock")
    return MUTATION_WORKSPACE


def run_mutation(*, update_baseline: bool = False) -> dict[str, dict[str, int | float]]:
    if platform.system() == "Windows":
        raise QualityFailure("mutmut 3 requires fork; run quality-nightly on GitHub Ubuntu or inside WSL")
    workspace = _stage_mutation_workspace()
    result = _python_module("mutmut", "run", check=False, report="mutmut-run.txt", cwd=workspace)
    if result.returncode:
        raise QualityFailure("mutmut failed to complete its mutation run")
    _python_module("mutmut", "results", "--all=true", report="mutmut-results.txt", cwd=workspace)
    current = _mutation_snapshot(workspace / "mutants")
    if not update_baseline:
        check_mutation(current, _load_baseline().get("mutation", {}))
    return current


def run_load_test() -> None:
    _python_module("quality.load_test")


def run_nightly() -> None:
    run_pr()
    for seed in (0, 7, 42):
        run_tests("--hypothesis-profile", "nightly", "--hypothesis-seed", str(seed))
    run_load_test()
    run_mutation()


def update_baseline() -> None:
    """Regenerate tracked files; no other public command writes them."""

    REPORTS.mkdir(parents=True, exist_ok=True)
    snapshot, fatal = collect_static()
    raise_failures(fatal)
    coverage_report = run_coverage()
    snapshot["coverage"] = {"percent": round(_coverage_percent(coverage_report), 4)}
    existing = _load_baseline() if BASELINE_PATH.exists() else {}
    if os.environ.get("QUALITY_UPDATE_MUTATION") == "1":
        snapshot["mutation"] = run_mutation(update_baseline=True)
    else:
        snapshot["mutation"] = existing.get("mutation", {})
    snapshot["bandit_rationale"] = BANDIT_RATIONALE
    snapshot["initial_measurements"] = INITIAL_MEASUREMENTS
    snapshot["schema_version"] = 1
    BASELINE_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run_pyrefly(update_baseline=True)
    update_secrets_baseline()


def run_precommit_ruff(files: Sequence[str]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    check_changed_ruff([file for file in files if Path(file).suffix in {".py", ".pyi"}])
