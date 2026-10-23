# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — finite owned tool execution and reaping

"""Execute fixed tool vectors without a shell and always reap the owned child."""

import asyncio
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from groundtruth_validation.report import Finding, Refusal


@dataclass(frozen=True)
class ToolResult:
    """Retain the actual completed tool result without interpreting success.

    Parameters
    ----------
    returncode : int
        Actual reaped child exit code.
    stdout : bytes
        Captured standard output within the accepted output limit.
    stderr : bytes
        Captured diagnostic bytes, never automatically echoed to callers.
    """

    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass
class _Observation:
    """Retain an observed exit even when communication cannot yield a result."""

    returncode: int | None = None


async def _execute(
    arguments: Sequence[str],
    root: Path,
    timeout: float,
    payload: bytes | None,
    observation: _Observation,
) -> ToolResult:
    """Await actual child completion and perform unconditional owned-child cleanup."""
    child = await asyncio.create_subprocess_exec(
        *arguments,
        cwd=root,
        stdin=asyncio.subprocess.PIPE if payload is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(child.communicate(payload), timeout=timeout)
    finally:
        # Process.kill refuses an already reaped child before issuing any signal.
        # This also guarantees owned-child cleanup when communication cannot finish.
        with suppress(ProcessLookupError):
            child.kill()
        returncode = await child.wait()
        observation.returncode = returncode
    return ToolResult(returncode, stdout, stderr)


def run_tool(
    arguments: Sequence[str],
    *,
    root: Path,
    timeout: float,
    payload: bytes | None = None,
    maximum_output: int = 1_048_576,
) -> ToolResult:
    """Execute a fixed absolute tool with a deadline and output acceptance bound.

    Parameters
    ----------
    arguments : Sequence[str]
        Authored argument vector beginning with an absolute tool path.
    root : Path
        Actual child working directory.
    timeout : float
        Positive wall-clock deadline in seconds, at most 300.
    payload : bytes or None
        Optional finite standard input, without shell interpolation.
    maximum_output : int
        Maximum combined output accepted after completion, at most eight MiB.
        Peak process memory remains subject to the caller's reserved job budget.

    Returns
    -------
    ToolResult
        Actual reaped child exit and captured bytes, not a checker verdict.

    Raises
    ------
    Refusal
        Tool configuration, environment, output size or completion is invalid.
        Received command output and raw exceptions are never included.
    """
    if (
        not arguments
        or not Path(arguments[0]).is_absolute()
        or not 0 < timeout <= 300
        or not 0 < maximum_output <= 8_388_608
    ):
        raise Refusal(
            Finding("tool.configuration", ".", "Invalid fixed tool execution configuration.", 4)
        )
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise Refusal(
            Finding(
                "tool.context", ".", "Synchronous tool entry requires its own execution context.", 4
            )
        )
    observation = _Observation()
    try:
        result = asyncio.run(_execute(arguments, root, timeout, payload, observation))
    except (OSError, TimeoutError, ValueError) as exc:
        raise Refusal(
            Finding(
                "tool.unavailable",
                ".",
                "Required tool could not complete within its execution boundary.",
                3,
            ),
            returncode=observation.returncode,
        ) from exc
    if len(result.stdout) + len(result.stderr) > maximum_output:
        raise Refusal(
            Finding("tool.output", ".", "Tool output exceeds its acceptance bound."),
            returncode=result.returncode,
        )
    return result
