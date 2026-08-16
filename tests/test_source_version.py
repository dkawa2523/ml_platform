from ml_platform_core.source_version import git_revision


def test_git_revision_reads_symbolic_head(tmp_path):
    git_dir = tmp_path / ".git"
    branch = git_dir / "refs" / "heads" / "main"
    branch.parent.mkdir(parents=True)
    branch.write_text("a" * 40 + "\n", encoding="utf-8")
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    assert git_revision(tmp_path) == "a" * 40
    assert git_revision(tmp_path, short=True) == "a" * 7


def test_git_revision_accepts_immutable_commit_without_git_metadata(tmp_path):
    (tmp_path / ".git").mkdir()

    assert git_revision(tmp_path, "B" * 40) == "b" * 40
    assert git_revision(tmp_path, "not-a-revision") is None


def test_git_revision_reads_packed_ref(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/release\n", encoding="utf-8")
    (git_dir / "packed-refs").write_text(f"{'c' * 40} refs/heads/release\n", encoding="utf-8")

    assert git_revision(tmp_path) == "c" * 40
