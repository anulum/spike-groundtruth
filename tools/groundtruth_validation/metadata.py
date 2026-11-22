# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — independent metadata acceptance policy

"""Bind exact schema policy, local metadata, actual interpreter and raw lock."""

import hashlib
import platform
from pathlib import Path
from typing import cast

from groundtruth_validation.inputs import read_file, read_json
from groundtruth_validation.report import Finding, Refusal, Report

# Reviewed independently of the descriptor. Policy updates require code review.
SCHEMA_SHA256 = "982d28b11976002ab4f01ac4ce70811840a7f5d0ef70041d6ac37c57f2ece8ce"
SCHEMA_PATH = "schemas/repository-domain.schema.json"
METADATA_PATH = "repository-domain.json"


def validate_metadata(root: Path) -> tuple[Report, dict[str, object] | None, bytes]:
    """Validate the complete metadata operation without requiring its inventory.

    Parameters
    ----------
    root : Path
        Explicit repository root containing the reviewed schema and lock.

    Returns
    -------
    tuple[Report, dict[str, object] | None, bytes]
        Scoped report, accepted metadata when valid, and its raw bytes.
        Rejected inputs never supply usable metadata to inventory generation.
    """
    report = Report("repository_metadata", [])
    try:
        from jsonschema import Draft202012Validator
        from packaging.specifiers import InvalidSpecifier, SpecifierSet

        schema, schema_bytes = read_json(root, SCHEMA_PATH)
        if hashlib.sha256(schema_bytes).hexdigest() != SCHEMA_SHA256:
            raise Refusal(
                Finding("schema.identity", SCHEMA_PATH, "Schema differs from reviewed policy.", 4)
            )
        metadata, raw = read_json(root, METADATA_PATH)
        if not Draft202012Validator(schema).is_valid(metadata):
            raise Refusal(
                Finding(
                    "metadata.shape", METADATA_PATH, "Metadata violates the closed local schema."
                )
            )
        # Only the hash-bound closed schema above establishes these string types.
        tooling = cast(dict[str, str], metadata["tooling_python"])
        try:
            compatible = SpecifierSet(tooling["supported_range"])
        except InvalidSpecifier as exc:
            raise Refusal(
                Finding("python.range", METADATA_PATH, "Python range is not a valid specifier.", 4)
            ) from exc
        actual = platform.python_version()
        if tooling["actual_version"] != actual:
            report.findings.append(
                Finding(
                    "python.identity", METADATA_PATH, "Running Python differs from metadata.", 3
                )
            )
        if actual not in compatible or tooling["actual_version"] not in compatible:
            report.findings.append(
                Finding(
                    "python.compatibility",
                    METADATA_PATH,
                    "Python falls outside the declared range.",
                )
            )
        lock = read_file(root, "requirements-dev.txt")
        if hashlib.sha256(lock).hexdigest() != tooling["development_lock_sha256"]:
            report.findings.append(
                Finding("lock.identity", "requirements-dev.txt", "Development lock digest differs.")
            )
        if report.findings:
            return report, None, b""
        return report, metadata, raw
    except ImportError:
        report.findings.append(
            Finding(
                "tool.unavailable", ".venv", "Required locked Python libraries are unavailable.", 3
            )
        )
    except Refusal as exc:
        report.findings.append(exc.finding)
    return report, None, b""
