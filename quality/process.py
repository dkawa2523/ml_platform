"""Subprocess execution shared by quality workflows."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quality.gates import QualityFailure

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / ".quality" / "reports"


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


async def _execute(command: tuple[str, ...], env: Mapping[str, str], cwd: Path) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    if process.returncode is None:
        raise QualityFailure(f"Command did not terminate: {' '.join(command)}")
    return (
        process.returncode,
        stdout_bytes.decode("utf-8", errors="replace"),
        stderr_bytes.decode("utf-8", errors="replace"),
    )


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
    _emit_output(stdout, stderr, report)
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


def _emit_output(stdout: str, stderr: str, report: str | None) -> None:
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
