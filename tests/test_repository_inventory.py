# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — inventory command integration tests

"""Exercise inventory operation selection through the real public command."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

COMMAND = Path(__file__).resolve().parents[1] / "tools/check_repository_inventory.py"


@pytest.mark.parametrize(
    "arguments",
    [["--mode", "generate"], ["--mode", "verify", "--output", "new.json"], ["--mode", "unknown"]],
)
def test_invalid_inventory_invocations(arguments: list[str]) -> None:
    """Require an explicit output only for the generation operation."""
    result = subprocess.run(
        [sys.executable, str(COMMAND), *arguments],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 4
    assert json.loads(result.stdout)["status"] == "invalid"
    assert result.stderr == ""


def test_generation_is_not_complete_repository_acceptance(repository: Path) -> None:
    """Accept generation, but refuse complete verification of missing source paths."""
    generation = subprocess.run(
        [
            sys.executable,
            str(COMMAND),
            "--root",
            str(repository),
            "--mode",
            "generate",
            "--output",
            "capability-inventory.json",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert generation.returncode == 0
    assert json.loads(generation.stdout)["gate"] == "capability_inventory"
    before = (repository / "capability-inventory.json").read_bytes()
    verification = subprocess.run(
        [sys.executable, str(COMMAND), "--root", str(repository), "--json"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert verification.returncode == 3
    report = json.loads(verification.stdout)
    assert report["gate"] == "repository_inventory"
    assert {x["path"] for x in report["reasons"]} >= {"README.md", "tools/preflight.py", ".git"}
    assert (repository / "capability-inventory.json").read_bytes() == before
