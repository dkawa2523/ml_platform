"""Secret scan comparison and its explicit baseline update."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from quality.gates import QualityFailure, compare_counter, raise_failures
from quality.process import _command, _load_json_output

ROOT = Path(__file__).resolve().parents[1]
SECRETS_BASELINE_PATH = ROOT / ".secrets.baseline"
SECRETS_EXCLUDE = (
    r"(?:^|[\\/])(?:\.git|\.venv(?:-[^\\/]+)?|\.quality|\.import_linter_cache|\.mypy_cache|"
    r"\.ruff_cache|\.uv-cache(?:-codex)?|\.pytest_cache|\.hypothesis|mutants|outputs|data)(?:[\\/]|$)"
    r"|(?:^|[\\/])\.secrets\.baseline$"
)


def check_secrets() -> None:
    try:
        baseline = json.loads(SECRETS_BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualityFailure("detect-secrets baseline is missing or invalid") from exc
    failures = compare_counter("detect-secrets", _secret_counter(_scan_secrets()), _secret_counter(baseline))
    raise_failures(failures)


def update_secrets_baseline() -> None:
    parsed = _scan_secrets()
    try:
        current = json.loads(SECRETS_BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        current = {}
    if _without_timestamp(parsed) != _without_timestamp(current):
        SECRETS_BASELINE_PATH.write_text(json.dumps(parsed, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
                [str(filename).replace("\\", "/"), finding.get("type"), finding.get("hashed_secret")],
                separators=(",", ":"),
            )
            counter[key] += 1
    return counter


def _without_timestamp(report: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if key != "generated_at"}
