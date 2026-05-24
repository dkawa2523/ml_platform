from pathlib import Path


def test_pkgs_do_not_import_clearml():
    offenders = []
    for path in Path("pkgs").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from clearml" in text or "import clearml" in text:
            offenders.append(str(path))
    assert offenders == []
