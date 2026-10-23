# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — metadata CLI acceptance and rejection

"""Exercise actual descriptor, schema, interpreter and lock boundaries."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.native_process import run_isolated

COMMAND = Path(__file__).resolve().parents[1] / "tools/check_repository_metadata.py"


def run_metadata(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    """Invoke the real metadata CLI with a finite timeout.

    Parameters
    ----------
    root : Path
        Actual input repository.
    *extra : str
        Additional literal command arguments.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Reaped process with captured caller-safe output.
    """
    return subprocess.run(
        [sys.executable, str(COMMAND), "--root", str(root), "--json", *extra],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_actual_repository_is_deterministic(repository: Path) -> None:
    """Accept valid source bytes independently of an absent generated inventory."""
    first = run_metadata(repository)
    assert first.returncode == 0
    assert first.stderr == ""
    assert json.loads(first.stdout) == {
        "gate": "repository_metadata",
        "scope": "local_scaffold_infrastructure",
        "status": "pass",
        "reasons": [],
    }
    assert run_metadata(repository).stdout == first.stdout
    assert not (repository / "capability-inventory.json").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository_name", "OTHER-REPOSITORY"),
        ("owner_group", "OTHER-GROUP"),
        ("capabilities", ["groundtruth_stimulus.manifest.v1"]),
        ("claims", ["qualified"]),
        ("qualified_owned_schema_ids", ["groundtruth_stimulus.manifest.v1"]),
        ("domain_runtime_dependencies", ["other"]),
        ("planned_owned_schema_ids", []),
        ("unknown", "CONFIDENTIAL_PAYLOAD"),
    ],
)
def test_closed_identity_and_unearned_claims(repository: Path, field: str, value: object) -> None:
    """Refuse altered scope without echoing a received capability or secret."""
    path = repository / "repository-domain.json"
    descriptor = json.loads(path.read_text())
    descriptor[field] = value
    path.write_text(json.dumps(descriptor))
    result = run_metadata(repository)
    assert result.returncode == 2
    assert json.loads(result.stdout)["reasons"][0]["code"] == "metadata.shape"
    assert "CONFIDENTIAL_PAYLOAD" not in result.stdout + result.stderr


def test_schema_cannot_choose_weaker_policy(repository: Path) -> None:
    """Refuse a replacement schema even when it would accept every descriptor."""
    (repository / "schemas/repository-domain.schema.json").write_text('{"type":"object"}')
    result = run_metadata(repository)
    assert result.returncode == 4
    assert json.loads(result.stdout)["reasons"][0]["code"] == "schema.identity"


@pytest.mark.parametrize(
    ("changes", "exit_code", "codes"),
    [
        ({"supported_range": "CONFIDENTIAL_PAYLOAD"}, 4, ["python.range"]),
        ({"supported_range": ">=3.14"}, 2, ["python.compatibility"]),
        ({"actual_version": "3.13.0"}, 3, ["python.identity", "python.compatibility"]),
        ({"development_lock_sha256": "0" * 64}, 2, ["lock.identity"]),
        (
            {"actual_version": "3.13.0", "development_lock_sha256": "0" * 64},
            3,
            ["python.identity", "python.compatibility", "lock.identity"],
        ),
    ],
)
def test_semantic_toolchain_bindings(
    repository: Path, changes: dict[str, str], exit_code: int, codes: list[str]
) -> None:
    """Check real interpreter, semantic compatibility and raw lock digests."""
    path = repository / "repository-domain.json"
    descriptor = json.loads(path.read_text())
    descriptor["tooling_python"].update(changes)
    path.write_text(json.dumps(descriptor))
    result = run_metadata(repository)
    assert result.returncode == exit_code
    assert [item["code"] for item in json.loads(result.stdout)["reasons"]] == codes
    assert "CONFIDENTIAL_PAYLOAD" not in result.stdout + result.stderr


def test_real_lock_mutation_is_detected(repository: Path) -> None:
    """Bind the source lock's raw bytes, including comments and whitespace."""
    path = repository / "requirements-dev.txt"
    path.write_bytes(path.read_bytes() + b"\n")
    result = run_metadata(repository)
    assert result.returncode == 2
    assert json.loads(result.stdout)["reasons"][0]["code"] == "lock.identity"


def test_absent_locked_libraries_are_unavailable(repository: Path) -> None:
    """Run the real interpreter without site packages and refuse missing tools."""
    result = run_isolated(COMMAND, "--root", str(repository), "--json")
    assert result.returncode == 3
    assert result.stderr == ""
    assert json.loads(result.stdout)["reasons"][0]["code"] == "tool.unavailable"
