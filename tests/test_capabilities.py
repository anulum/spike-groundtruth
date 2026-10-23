# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — capability inventory file integration tests

"""Test deterministic exclusive output and source binding through public APIs."""

import hashlib
import json
from pathlib import Path

import pytest

from groundtruth_validation.capabilities import validate_capabilities


def test_generate_and_verify_actual_metadata(repository: Path) -> None:
    """Generate exact empty capabilities, then verify without changing any file."""
    assert validate_capabilities(repository, "capability-inventory.json").exit_code == 0
    output = repository / "capability-inventory.json"
    original = output.read_bytes()
    assert json.loads(original) == {
        "repository_name": "SPIKE-GROUNDTRUTH",
        "lifecycle": "local_scaffold",
        "evidence_maturity": "architecture_only",
        "capabilities": [],
        "claims": [],
        "qualified_owned_schema_ids": [],
        "source_metadata": {
            "path": "repository-domain.json",
            "sha256": hashlib.sha256(
                (repository / "repository-domain.json").read_bytes()
            ).hexdigest(),
        },
    }
    assert validate_capabilities(repository).exit_code == 0
    assert output.read_bytes() == original
    assert validate_capabilities(repository, "second.json").exit_code == 0
    assert (repository / "second.json").read_bytes() == original
    assert list(repository.glob(".inventory-*.tmp")) == []


def test_existing_output_is_never_replaced(repository: Path) -> None:
    """Keep existing data intact when exclusive publication encounters a collision."""
    output = repository / "existing.json"
    output.write_bytes(b"original content\n")
    report = validate_capabilities(repository, output.name)
    assert report.exit_code == 2
    assert report.findings[0].code == "output.exists"
    assert output.read_bytes() == b"original content\n"
    assert list(repository.glob(".inventory-*.tmp")) == []


@pytest.mark.parametrize("output", ["../outside.json", "/absolute.json", ""])
def test_output_namespace_is_bounded(repository: Path, output: str) -> None:
    """Refuse output names outside the repository-relative namespace."""
    report = validate_capabilities(repository, output)
    assert report.exit_code == 4
    assert report.findings[0].code == "output.invalid"


def test_missing_output_parent_is_unavailable(repository: Path) -> None:
    """Report actual output-directory failure without leaving partial output."""
    report = validate_capabilities(repository, "missing/new.json")
    assert report.exit_code == 3
    assert report.findings[0].code == "output.unavailable"
    assert not (repository / "missing").exists()


def test_linked_output_parent_is_refused(repository: Path) -> None:
    """Refuse a statically linked directory rather than publish through it."""
    (repository / "linked").symlink_to(repository, target_is_directory=True)
    report = validate_capabilities(repository, "linked/new.json")
    assert report.exit_code == 2
    assert report.findings[0].code == "output.link"
    assert not (repository / "new.json").exists()


def test_inventory_source_and_claims_must_match(repository: Path) -> None:
    """Refuse altered capabilities and changed exact source formatting."""
    assert validate_capabilities(repository, "capability-inventory.json").exit_code == 0
    output = repository / "capability-inventory.json"
    original = output.read_bytes()
    content = json.loads(original)
    content["claims"] = ["qualified"]
    output.write_text(json.dumps(content))
    report = validate_capabilities(repository)
    assert report.exit_code == 2
    assert report.findings[0].code == "inventory.identity"
    output.write_bytes(original)
    metadata = repository / "repository-domain.json"
    metadata.write_bytes(metadata.read_bytes() + b"\n")
    assert validate_capabilities(repository).findings[0].code == "inventory.identity"


def test_missing_inventory_does_not_become_pass(repository: Path) -> None:
    """Keep the absence of the canonical generated file as unavailable."""
    report = validate_capabilities(repository)
    assert report.exit_code == 3
    assert report.findings[0].code == "file.unavailable"


def test_refused_metadata_cannot_generate_output(repository: Path) -> None:
    """Carry a metadata refusal forward without writing an inventory."""
    (repository / "repository-domain.json").write_text('{"claims":["qualified"]}')
    report = validate_capabilities(repository, "new.json")
    assert report.exit_code == 2
    assert report.findings[0].code == "metadata.shape"
    assert not (repository / "new.json").exists()
