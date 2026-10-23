# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — actual finite tool execution tests

"""Exercise actual child completion, input, output and configuration boundaries."""

import asyncio
import sys
from pathlib import Path

import pytest

from groundtruth_validation.execution import run_tool
from groundtruth_validation.report import Refusal


def test_real_exit_stdout_and_stderr(tmp_path: Path) -> None:
    """Preserve a completed interpreter's actual nonzero exit and both streams."""
    result = run_tool(
        [sys.executable, "-c", 'import sys; print("out"); sys.stderr.write("err"); sys.exit(7)'],
        root=tmp_path,
        timeout=10,
    )
    assert result.returncode == 7
    assert result.stdout == b"out\n"
    assert result.stderr == b"err"


def test_literal_input_is_not_shell_interpreted(tmp_path: Path) -> None:
    """Pass received bytes through actual standard input without shell expansion."""
    payload = b"$(not-a-command)\x00finite input\n"
    result = run_tool(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
        root=tmp_path,
        timeout=10,
        payload=payload,
    )
    assert result.returncode == 0
    assert result.stdout == payload


@pytest.mark.parametrize(
    ("arguments", "timeout", "maximum"),
    [
        ([], 1, 100),
        (["relative"], 1, 100),
        ([sys.executable], 0, 100),
        ([sys.executable], 301, 100),
        ([sys.executable], 1, 0),
        ([sys.executable], 1, 8_388_609),
    ],
)
def test_invalid_execution_configuration(
    tmp_path: Path, arguments: list[str], timeout: float, maximum: int
) -> None:
    """Refuse invalid tools or unbounded execution configuration before launch."""
    with pytest.raises(Refusal) as caught:
        run_tool(arguments, root=tmp_path, timeout=timeout, maximum_output=maximum)
    assert caught.value.finding.code == "tool.configuration"


def test_missing_real_executable(tmp_path: Path) -> None:
    """Keep an unavailable executable as a safe authored unavailable result."""
    with pytest.raises(Refusal) as caught:
        run_tool([str(tmp_path / "absent-executable")], root=tmp_path, timeout=10)
    assert caught.value.finding.code == "tool.unavailable"
    assert caught.value.finding.exit_code == 3


def test_completed_output_acceptance_limit(tmp_path: Path) -> None:
    """Reject ordinary completed version output when it exceeds a configured limit."""
    with pytest.raises(Refusal) as caught:
        run_tool([sys.executable, "--version"], root=tmp_path, timeout=10, maximum_output=1)
    assert caught.value.finding.code == "tool.output"


def test_existing_event_loop_requires_separate_context(tmp_path: Path) -> None:
    """Refuse synchronous nesting inside a real active event loop before launch."""

    async def invoke() -> None:
        """Call the public synchronous API from a real existing loop."""
        with pytest.raises(Refusal) as caught:
            run_tool([sys.executable, "--version"], root=tmp_path, timeout=10)
        assert caught.value.finding.code == "tool.context"

    asyncio.run(invoke())
