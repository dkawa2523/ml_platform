"""Git revision lookup shared by local and ClearML runtimes."""

from __future__ import annotations

import re
from pathlib import Path

COMMIT_PATTERN = re.compile(r"[0-9a-fA-F]{40}")


def git_revision(
    repository: Path,
    revision: str = "HEAD",
    *,
    short: bool = False,
) -> str | None:
    """Resolve HEAD, a full commit, or a local ref without spawning git."""
    git_dir = _git_directory(repository)
    if git_dir is None:
        return None
    commit = _resolve_revision(git_dir, revision.strip())
    if commit is None:
        return None
    return commit[:7] if short else commit


def _git_directory(repository: Path) -> Path | None:
    dot_git = repository.resolve() / ".git"
    if dot_git.is_dir():
        return dot_git
    if not dot_git.is_file():
        return None
    pointer = dot_git.read_text(encoding="utf-8").strip()
    if not pointer.startswith("gitdir:"):
        return None
    path = Path(pointer.removeprefix("gitdir:").strip())
    return path if path.is_absolute() else (repository / path).resolve()


def _resolve_revision(git_dir: Path, revision: str) -> str | None:
    if COMMIT_PATTERN.fullmatch(revision):
        return revision.lower()
    if revision == "HEAD":
        return _read_ref_file(git_dir, git_dir / "HEAD")
    candidates = (
        revision,
        f"refs/heads/{revision}",
        f"refs/tags/{revision}",
        f"refs/remotes/{revision}",
    )
    return next((commit for ref in candidates if (commit := _read_ref(git_dir, ref)) is not None), None)


def _read_ref_file(git_dir: Path, path: Path) -> str | None:
    if not path.is_file():
        return None
    value = path.read_text(encoding="utf-8").strip()
    if value.startswith("ref:"):
        return _read_ref(git_dir, value.removeprefix("ref:").strip())
    return value.lower() if COMMIT_PATTERN.fullmatch(value) else None


def _read_ref(git_dir: Path, ref: str) -> str | None:
    for directory in _ref_directories(git_dir):
        commit = _read_ref_file(git_dir, directory / ref)
        if commit is not None:
            return commit
        packed_refs = directory / "packed-refs"
        if not packed_refs.is_file():
            continue
        for line in packed_refs.read_text(encoding="utf-8").splitlines():
            if line.startswith(("#", "^")):
                continue
            commit, _, packed_ref = line.partition(" ")
            if packed_ref == ref and COMMIT_PATTERN.fullmatch(commit):
                return commit.lower()
    return None


def _ref_directories(git_dir: Path) -> tuple[Path, ...]:
    common_pointer = git_dir / "commondir"
    if not common_pointer.is_file():
        return (git_dir,)
    common = Path(common_pointer.read_text(encoding="utf-8").strip())
    common = common if common.is_absolute() else (git_dir / common).resolve()
    return (git_dir, common)
