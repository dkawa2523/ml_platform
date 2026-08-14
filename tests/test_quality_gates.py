from __future__ import annotations

import json
from pathlib import Path

import pytest

from quality import runner
from quality.gates import (
    QualityFailure,
    compare_complexity,
    compare_counter,
    diagnostic_counter,
    fatal_diagnostics,
)


def _ruff(path: Path, line: int, *, code: str = "I001", message: str = "Import block is unsorted") -> dict:
    return {
        "code": code,
        "filename": str(path),
        "location": {"row": line, "column": 1},
        "message": message,
    }


def test_diagnostic_fingerprint_is_stable_when_line_moves(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text("\n\ndef calculate():\n    return 1\n", encoding="utf-8")

    before = diagnostic_counter([_ruff(source, 3)], tmp_path, tool="ruff")
    source.write_text("\n\n\n\ndef calculate():\n    return 1\n", encoding="utf-8")
    after = diagnostic_counter([_ruff(source, 5)], tmp_path, tool="ruff")

    assert before == after
    assert compare_counter("Ruff", after, before) == []


def test_counter_fails_new_and_increased_but_allows_improvement():
    assert compare_counter("tool", {"known": 1}, {"known": 2}) == []
    assert compare_counter("tool", {"known": 2}, {"known": 1})
    assert compare_counter("tool", {"new": 1}, {})


def test_complexity_fails_new_hotspot_and_existing_increase():
    assert compare_complexity({"module.py::new": 11}, {})
    assert compare_complexity({"module.py::old": 12}, {"module.py::old": 11})
    assert compare_complexity({"module.py::old": 9}, {"module.py::old": 11}) == []


def test_fatal_diagnostics_cannot_be_baselined(tmp_path):
    ruff = [_ruff(tmp_path / "broken.py", 1, code="F821", message="Undefined name")]
    bandit = [
        {
            "test_id": "B999",
            "filename": str(tmp_path / "unsafe.py"),
            "issue_text": "critical issue",
            "issue_severity": "HIGH",
        }
    ]

    failures = fatal_diagnostics(ruff, bandit)

    assert any("F821" in failure for failure in failures)
    assert any("B999" in failure for failure in failures)


def test_coverage_regression_is_nonzero_quality_failure():
    with pytest.raises(QualityFailure, match="coverage dropped"):
        runner.check_coverage({"totals": {"percent_covered": 80.9}}, {"coverage": {"percent": 81.0}})


def test_secret_regression_is_nonzero_quality_failure(monkeypatch, tmp_path):
    baseline = tmp_path / ".secrets.baseline"
    baseline.write_text('{"results": {}}', encoding="utf-8")
    monkeypatch.setattr(runner, "SECRETS_BASELINE_PATH", baseline)
    digest_field = "hashed_" + "secret"
    monkeypatch.setattr(
        runner,
        "_scan_secrets",
        lambda: {"results": {"tracked.py": [{"type": "Secret Keyword", digest_field: "review-required"}]}},
    )

    with pytest.raises(QualityFailure, match="detect-secrets"):
        runner.check_secrets()


def test_architecture_command_failure_is_nonzero(monkeypatch):
    def broken_contract(*args, **kwargs):
        raise QualityFailure("import contract broken")

    monkeypatch.setattr(runner, "_command", broken_contract)

    with pytest.raises(QualityFailure, match="import contract broken"):
        runner.run_architecture()


def test_dependency_audit_failure_cannot_be_recorded_as_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "REPORTS", tmp_path)
    monkeypatch.setattr(runner, "_command", lambda *args, **kwargs: runner.CommandResult((), 0, "", ""))
    monkeypatch.setattr(
        runner,
        "_python_module",
        lambda *args, **kwargs: runner.CommandResult(("pip-audit",), 1, "", "network failure"),
    )

    with pytest.raises(QualityFailure, match="did not complete"):
        runner._pip_audit()


def test_mutation_snapshot_is_grouped_by_module(tmp_path):
    metadata = tmp_path / "package" / "module.py.meta"
    metadata.parent.mkdir()
    metadata.write_text(
        json.dumps({"exit_code_by_key": {"killed": 1, "typed": 37, "survived": 0, "untested": 5}}),
        encoding="utf-8",
    )

    snapshot = runner._mutation_snapshot(tmp_path)

    assert snapshot["package/module.py"] == {
        "killed": 2,
        "survived": 1,
        "untested": 1,
        "incomplete": 0,
        "total": 4,
        "kill_rate": 50.0,
    }


def test_mutation_gate_rejects_weaker_module_results():
    baseline = {
        "module.py": {"killed": 8, "survived": 1, "untested": 1, "incomplete": 0, "total": 10, "kill_rate": 80.0}
    }
    current = {
        "module.py": {"killed": 7, "survived": 2, "untested": 1, "incomplete": 0, "total": 10, "kill_rate": 70.0}
    }

    with pytest.raises(QualityFailure, match="survived increased"):
        runner.check_mutation(current, baseline)


def test_fast_and_pr_do_not_write_tracked_baselines(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "ruff": {},
                "bandit": {},
                "complexity": {},
                "pip_audit": {},
                "vulture": {},
                "coverage": {"percent": 81.0},
            }
        ),
        encoding="utf-8",
    )
    original = baseline.read_bytes()
    monkeypatch.setattr(runner, "BASELINE_PATH", baseline)
    monkeypatch.setattr(runner, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(runner, "changed_python_files", lambda: [])
    monkeypatch.setattr(runner, "run_pyrefly", lambda: None)
    monkeypatch.setattr(runner, "run_tests", lambda *args: None)
    runner.run_fast()
    monkeypatch.setattr(runner, "_python_module", lambda *args, **kwargs: runner.CommandResult((), 0, "", ""))
    monkeypatch.setattr(
        runner,
        "collect_static",
        lambda: ({key: {} for key in ("ruff", "bandit", "complexity", "pip_audit", "vulture")}, []),
    )
    monkeypatch.setattr(runner, "run_architecture", lambda: None)
    monkeypatch.setattr(runner, "run_coverage", lambda: {"totals": {"percent_covered": 81.0}})
    monkeypatch.setattr(runner, "run_diff_coverage", lambda: None)
    monkeypatch.setattr(runner, "check_secrets", lambda: None)
    monkeypatch.setattr(runner, "run_smoke", lambda: None)
    runner.run_pr()

    assert baseline.read_bytes() == original
