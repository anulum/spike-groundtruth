# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — finite repository input fixtures

"""Provide actual source inputs for public validator integration tests."""

import json
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Create a finite metadata repository from the actual governed inputs.

    Parameters
    ----------
    tmp_path : Path
        Per-test Samsung temporary directory.

    Returns
    -------
    Path
        Isolated file-input directory, without a domain producer substitute.
    """
    for relative in (
        "repository-domain.json",
        "schemas/repository-domain.schema.json",
        "requirements-dev.txt",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPOSITORY / relative).read_bytes())
    return tmp_path


@pytest.fixture
def workflow_repository(tmp_path: Path) -> Path:
    """Supply the actual complete reviewed workflow configuration inputs.

    Parameters
    ----------
    tmp_path : Path
        Finite per-test input directory.

    Returns
    -------
    Path
        Independent configuration files, without emulated hosted execution.
    """
    policy = json.loads((REPOSITORY / "workflow-policy.json").read_text())
    paths = ["workflow-policy.json", "workflow-provenance.json"]
    paths.extend(".github/workflows/" + name for name in policy["workflow_sha256"])
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPOSITORY / relative).read_bytes())
    return tmp_path
