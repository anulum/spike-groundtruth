# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — deterministic capability inventory publication

"""Generate exclusive capability inventories from fully accepted metadata."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from groundtruth_validation.inputs import read_json
from groundtruth_validation.metadata import validate_metadata
from groundtruth_validation.report import Finding, Refusal, Report


def inventory_bytes(raw_metadata: bytes) -> bytes:
    """Construct the independently expected empty initial capability inventory.

    Parameters
    ----------
    raw_metadata : bytes
        Exact source bytes already accepted by the complete metadata gate.

    Returns
    -------
    bytes
        Stable UTF-8 JSON, without a self-digest or qualified domain claim.
    """
    return (
        json.dumps(
            {
                "repository_name": "SPIKE-GROUNDTRUTH",
                "lifecycle": "local_scaffold",
                "evidence_maturity": "architecture_only",
                "capabilities": [],
                "claims": [],
                "qualified_owned_schema_ids": [],
                "source_metadata": {
                    "path": "repository-domain.json",
                    "sha256": hashlib.sha256(raw_metadata).hexdigest(),
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def create_inventory(root: Path, output: str, content: bytes) -> None:
    """Publish a complete new inventory atomically without replacing any path.

    Parameters
    ----------
    root : Path
        Validated repository root.
    output : str
        Caller-chosen new repository-relative output file.
    content : bytes
        Complete deterministic inventory bytes.

    Raises
    ------
    Refusal
        The path is invalid, already present, linked, or unavailable.
    """
    relative = Path(output)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise Refusal(Finding("output.invalid", ".", "Output must be a new relative file.", 4))
    parent = root
    for part in relative.parts[:-1]:
        parent /= part
        if parent.is_symlink():
            raise Refusal(Finding("output.link", ".", "Linked output directory is not accepted."))
    try:
        with tempfile.NamedTemporaryFile(dir=parent, prefix=".inventory-", suffix=".tmp") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            os.link(stream.name, root / relative)
    except FileExistsError as exc:
        raise Refusal(
            Finding("output.exists", ".", "Output already exists; no file was replaced.")
        ) from exc
    except OSError as exc:
        raise Refusal(
            Finding("output.unavailable", ".", "Inventory output is unavailable.", 3)
        ) from exc


def validate_capabilities(root: Path, output: str | None = None) -> Report:
    """Generate exclusively or verify existing capability bytes without mutation.

    Parameters
    ----------
    root : Path
        Repository containing accepted metadata and its exact lock.
    output : str or None
        New relative output for generation; None verifies the canonical file.

    Returns
    -------
    Report
        Result for capability inventory only, not complete repository readiness.
    """
    metadata_report, metadata, raw = validate_metadata(root)
    report = Report("capability_inventory", metadata_report.findings)
    if metadata is None:
        return report
    expected = inventory_bytes(raw)
    try:
        if output is not None:
            create_inventory(root, output, expected)
        else:
            _, actual = read_json(root, "capability-inventory.json")
            if actual != expected:
                report.findings.append(
                    Finding(
                        "inventory.identity",
                        "capability-inventory.json",
                        "Inventory differs from deterministic accepted metadata output.",
                    )
                )
    except Refusal as exc:
        report.findings.append(exc.finding)
    return report
