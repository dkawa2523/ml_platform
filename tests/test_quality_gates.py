from __future__ import annotations

import json
from pathlib import Path

import pytest

from quality import mutation, runner, secrets, static_analysis
from quality.gates import (
    QualityFailure,
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


def test_secret_regression_is_nonzero_quality_failure(monkeypatch, tmp_path):
    baseline = tmp_path / ".secrets.baseline"
    baseline.write_text('{"results": {}}', encoding="utf-8")
    monkeypatch.setattr(secrets, "SECRETS_BASELINE_PATH", baseline)
    digest_field = "hashed_" + "secret"
    monkeypatch.setattr(
        secrets,
        "_scan_secrets",
        lambda: {"results": {"tracked.py": [{"type": "Secret Keyword", digest_field: "review-required"}]}},
    )

    with pytest.raises(QualityFailure, match="detect-secrets"):
        secrets.check_secrets()


def test_secret_fingerprint_is_independent_of_path_separator():
    digest_field = "hashed_" + "secret"
    finding = {"type": "Secret Keyword", digest_field: "reviewed"}
    windows_report = {"results": {r"deploy\base\secret.example.yaml": [finding]}}
    posix_report = {"results": {"deploy/base/secret.example.yaml": [finding]}}

    assert secrets._secret_counter(windows_report) == secrets._secret_counter(posix_report)


def test_architecture_command_failure_is_nonzero(monkeypatch):
    def broken_contract(*args, **kwargs):
        raise QualityFailure("import contract broken")

    monkeypatch.setattr(runner, "_command", broken_contract)

    with pytest.raises(QualityFailure, match="import contract broken"):
        runner.run_architecture()


def test_branch_coverage_gate_rejects_a_regression():
    with pytest.raises(QualityFailure, match="Branch coverage decreased"):
        runner.check_branch_coverage(
            {"branch_percent": 79.5},
            {"coverage": {"branch_percent": 80.0}},
        )

    runner.check_branch_coverage(
        {"branch_percent": 80.1},
        {"coverage": {"branch_percent": 80.0}},
    )


def test_dependency_audit_failure_cannot_be_recorded_as_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(static_analysis, "REPORTS", tmp_path)
    monkeypatch.setattr(static_analysis, "_command", lambda *args, **kwargs: runner.CommandResult((), 0, "", ""))
    monkeypatch.setattr(
        static_analysis,
        "_python_module",
        lambda *args, **kwargs: runner.CommandResult(("pip-audit",), 1, "", "network failure"),
    )

    with pytest.raises(QualityFailure, match="did not complete"):
        static_analysis._run_pip_audit()


def test_dependency_vulnerabilities_are_never_baselined(monkeypatch, tmp_path):
    monkeypatch.setattr(static_analysis, "REPORTS", tmp_path)
    monkeypatch.setattr(static_analysis, "_command", lambda *args, **kwargs: runner.CommandResult((), 0, "", ""))
    report = {"dependencies": [{"name": "unsafe", "vulns": [{"id": "CVE-example"}]}]}
    monkeypatch.setattr(
        static_analysis,
        "_python_module",
        lambda *args, **kwargs: runner.CommandResult(("pip-audit",), 1, json.dumps(report), ""),
    )

    with pytest.raises(QualityFailure, match="unsafe:CVE-example"):
        static_analysis._run_pip_audit()


def test_mutation_snapshot_is_grouped_by_module(tmp_path):
    metadata = tmp_path / "package" / "module.py.meta"
    metadata.parent.mkdir()
    metadata.write_text(
        json.dumps({"exit_code_by_key": {"killed": 1, "typed": 37, "survived": 0, "untested": 5}}),
        encoding="utf-8",
    )

    snapshot = mutation.mutation_snapshot(tmp_path)

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
        mutation.check_mutation(current, baseline)


def test_fast_and_pr_do_not_write_tracked_baselines(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps({"ruff": {}, "bandit": {}, "coverage": {"branch_percent": 80.0}}),
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
        lambda: ({"ruff": {}, "bandit": {}}, []),
    )
    monkeypatch.setattr(runner, "run_architecture", lambda: None)
    monkeypatch.setattr(runner, "run_coverage", lambda: {"branch_percent": 80.0})
    monkeypatch.setattr(runner, "run_diff_coverage", lambda: None)
    monkeypatch.setattr(runner, "check_secrets", lambda: None)
    monkeypatch.setattr(runner, "run_smoke", lambda: None)
    runner.run_pr()

    assert baseline.read_bytes() == original
