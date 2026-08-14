"""Stable entry points for repository quality checks."""

from __future__ import annotations

import nox

nox.options.default_venv_backend = "none"


def _quality(session: nox.Session, command: str) -> None:
    session.run("python", "-m", "quality", command, *session.posargs)


@nox.session(name="quality-fast", venv_backend="none")
def quality_fast(session: nox.Session) -> None:
    """Format changed Python files and run the development gate."""

    _quality(session, "fast")


@nox.session(name="quality-pr", venv_backend="none")
def quality_pr(session: nox.Session) -> None:
    """Run the complete pull-request quality gate."""

    _quality(session, "pr")


@nox.session(name="quality-nightly", venv_backend="none")
def quality_nightly(session: nox.Session) -> None:
    """Run expensive multi-seed, load, and mutation checks."""

    _quality(session, "nightly")


@nox.session(name="quality-baseline", venv_backend="none")
def quality_baseline(session: nox.Session) -> None:
    """Explicitly regenerate tracked quality baselines."""

    _quality(session, "baseline")
