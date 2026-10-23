# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — command invocation and output boundary tests

"""Exercise actual argument parsing and operating-system output failures."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from groundtruth_validation.cli import metadata_main

COMMAND = Path(__file__).resolve().parents[1] / "tools/check_repository_metadata.py"


@pytest.mark.parametrize("args", [["--unknown", "CONFIDENTIAL_PAYLOAD"], ["--root"]])
def test_invalid_invocation_is_safe(args: list[str]) -> None:
    """Return parseable invalid-invocation JSON without rejected argument text."""
    result = subprocess.run(
        [sys.executable, str(COMMAND), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 4
    assert result.stderr == ""
    assert "CONFIDENTIAL_PAYLOAD" not in result.stdout
    assert json.loads(result.stdout)["reasons"][0]["code"] == "cli.invalid"


def test_default_root_and_json_report(repository: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Use the real current directory when no root option is supplied."""
    monkeypatch.chdir(repository)
    assert metadata_main([]) == 0


def test_real_output_failure_never_passes(repository: Path) -> None:
    """Refuse when Linux's actual full device cannot receive the report."""
    with Path("/dev/full").open("w") as output:
        result = subprocess.run(
            [sys.executable, str(COMMAND), "--root", str(repository)],
            stdout=output,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=10,
        )
    assert result.returncode == 3
    assert "Traceback" not in result.stderr
