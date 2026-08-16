"""Mutation result parsing, comparison, and isolated workspace setup."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from quality.gates import QualityFailure, raise_failures

_STATUS_BY_EXIT_CODE = {
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


def mutation_snapshot(mutants_root: Path) -> dict[str, dict[str, int | float]]:
    snapshots: dict[str, dict[str, int | float]] = {}
    for metadata_path in sorted(mutants_root.rglob("*.py.meta")):
        metadata = _load_metadata(metadata_path)
        statuses = Counter(_STATUS_BY_EXIT_CODE.get(code, "suspicious") for code in metadata.values())
        snapshots[_module_name(metadata_path, mutants_root)] = _module_snapshot(statuses)
    if not snapshots:
        raise QualityFailure("mutmut produced no module metadata")
    return snapshots


def _load_metadata(metadata_path: Path) -> Mapping[str, int | None]:
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return metadata.get("exit_code_by_key", {})
    except (AttributeError, OSError, json.JSONDecodeError) as exc:
        raise QualityFailure(f"Invalid mutmut metadata: {metadata_path}") from exc


def _module_name(metadata_path: Path, mutants_root: Path) -> str:
    module_path = metadata_path.relative_to(mutants_root).with_suffix("")
    if module_path.parts[:1] == ("src",):
        module_path = Path(*module_path.parts[1:])
    return module_path.as_posix()


def _module_snapshot(statuses: Counter[str]) -> dict[str, int | float]:
    total = sum(statuses.values())
    killed = statuses["killed"]
    return {
        "killed": killed,
        "survived": statuses["survived"],
        "untested": statuses["untested"],
        "incomplete": total - killed - statuses["survived"] - statuses["untested"],
        "total": total,
        "kill_rate": round(100.0 * killed / total, 4) if total else 0.0,
    }


def check_mutation(
    current: Mapping[str, Mapping[str, int | float]],
    baseline: Mapping[str, Mapping[str, int | float]],
) -> None:
    failures = [failure for module, stats in current.items() for failure in _module_failures(module, stats, baseline)]
    failures.extend(
        f"mutmut: baseline module was not evaluated: {module}" for module in sorted(set(baseline) - set(current))
    )
    raise_failures(failures)


def _module_failures(
    module: str,
    stats: Mapping[str, int | float],
    baseline: Mapping[str, Mapping[str, int | float]],
) -> list[str]:
    previous = baseline.get(module)
    if previous is None:
        return [f"mutmut: {module} has no baseline"]
    failures: list[str] = []
    if int(stats["incomplete"]):
        failures.append(f"mutmut: {module} has {stats['incomplete']} incomplete mutants")
    for field in ("survived", "untested"):
        if int(stats[field]) > int(previous[field]):
            failures.append(f"mutmut: {module} {field} increased from {previous[field]} to {stats[field]}")
    if float(stats["kill_rate"]) + 1e-9 < float(previous["kill_rate"]):
        failures.append(f"mutmut: {module} kill rate dropped from {previous['kill_rate']}% to {stats['kill_rate']}%")
    return failures


def stage_workspace(root: Path, workspace: Path) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    for name in ("src", "tests", "config", "clearml"):
        target = workspace / name
        if target.exists():
            shutil.rmtree(target)
    source = workspace / "src"
    source.mkdir()
    shutil.copytree(root / "pkgs/core/src/ml_platform_core", source / "ml_platform_core")
    shutil.copytree(root / "pkgs/tabular/src/ml_platform_tabular", source / "ml_platform_tabular")
    for name in ("tests", "config", "clearml"):
        shutil.copytree(root / name, workspace / name)
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy2(root / name, workspace / name)
    return workspace
