# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — closed dependency observation records

"""Read actual development dependency provenance without selecting executable code."""

from pathlib import Path
from typing import NotRequired, TypedDict, cast

from groundtruth_validation.inputs import read_json
from groundtruth_validation.report import Finding, Refusal


class Artifact(TypedDict):
    """Describe one allowed exact-version release artifact."""

    filename: str
    url: str
    sha256: str
    kind: str


class LicenseEvidence(TypedDict):
    """Identify exact installed licence text without interpreting its permissions."""

    path: str
    sha256: str


class LicenseSource(TypedDict):
    """Bind a custom licence identity to its exact upstream source."""

    url: str
    commit: str
    git_blob_sha: str
    sha256: str
    detected_spdx: str


class PackageRecord(TypedDict):
    """Retain a complete package observation and its independent source identities."""

    name: str
    version: str
    role: str
    metadata_source: str
    metadata_sha256: str
    record_sha256: str
    declared_license_expression: str | None
    declared_license: str | None
    license_classifiers: list[str]
    license_evidence: list[LicenseEvidence]
    allowed_artifacts: list[Artifact]
    installer: str
    license_expression: str
    license_basis: str
    license_source: NotRequired[LicenseSource]


SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
TEXT = {"type": "string", "minLength": 1}
NULLABLE_TEXT = {"type": ["string", "null"]}
PACKAGE_PROPERTIES: dict[str, object] = {
    **{
        name: TEXT
        for name in (
            "name",
            "version",
            "role",
            "metadata_source",
            "installer",
            "license_expression",
            "license_basis",
        )
    },
    "metadata_sha256": SHA,
    "record_sha256": SHA,
    "declared_license_expression": NULLABLE_TEXT,
    "declared_license": NULLABLE_TEXT,
    "license_classifiers": {"type": "array", "items": TEXT},
    "license_evidence": {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["path", "sha256"],
            "properties": {"path": TEXT, "sha256": SHA},
        },
    },
    "allowed_artifacts": {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["filename", "url", "sha256", "kind"],
            "properties": {
                "filename": TEXT,
                "url": TEXT,
                "sha256": SHA,
                "kind": {"enum": ["sdist", "bdist_wheel"]},
            },
        },
    },
    "license_source": {
        "type": "object",
        "additionalProperties": False,
        "required": ["url", "commit", "git_blob_sha", "sha256", "detected_spdx"],
        "properties": {
            "url": TEXT,
            "commit": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "git_blob_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "sha256": SHA,
            "detected_spdx": TEXT,
        },
    },
}
PROVENANCE_PROPERTIES: dict[str, object] = {
    **{
        name: TEXT
        for name in (
            "observed_utc",
            "scope",
            "python_version",
            "artifact_semantics",
            "artifact_platform",
        )
    },
    "lock_sha256": SHA,
    "packages": {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": [name for name in PACKAGE_PROPERTIES if name != "license_source"],
            "properties": PACKAGE_PROPERTIES,
        },
    },
}
PROVENANCE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": list(PROVENANCE_PROPERTIES),
    "properties": PROVENANCE_PROPERTIES,
}


def read_provenance(root: Path) -> tuple[dict[str, object], list[PackageRecord]]:
    """Validate closed records, unique names and actual SPDX or custom identities.

    Parameters
    ----------
    root : Path
        Repository containing its recorded development provenance.

    Returns
    -------
    tuple[dict[str, object], list[PackageRecord]]
        Validated observation metadata and package records, not runtime acceptance.

    Raises
    ------
    Refusal
        Records are ambiguous, malformed or have an invalid licence identity.
    """
    try:
        from jsonschema import Draft202012Validator
        from packaging.licenses import InvalidLicenseExpression, canonicalize_license_expression
        from packaging.utils import canonicalize_name
    except ImportError as exc:
        raise Refusal(
            Finding(
                "dependency.tool",
                ".venv",
                "Locked provenance schema or licence parser is unavailable.",
                3,
            )
        ) from exc

    source, _ = read_json(root, "dependency-provenance.json")
    if not Draft202012Validator(PROVENANCE_SCHEMA).is_valid(source):
        raise Refusal(
            Finding(
                "dependency.records",
                "dependency-provenance.json",
                "Dependency records violate the closed observation schema.",
            )
        )
    # The complete closed schema above establishes every nested record type.
    records = cast(list[PackageRecord], source["packages"])
    names: set[str] = set()
    for record in records:
        name = canonicalize_name(record["name"])
        if name != record["name"] or name in names:
            raise Refusal(
                Finding(
                    "dependency.names",
                    "dependency-provenance.json",
                    "Dependency names must be unique canonical identities.",
                )
            )
        names.add(name)
        try:
            canonicalize_license_expression(record["license_expression"])
        except InvalidLicenseExpression as exc:
            raise Refusal(
                Finding(
                    "dependency.licence",
                    "dependency-provenance.json",
                    "Recorded licence expression is invalid.",
                )
            ) from exc
        if record["license_expression"].startswith("LicenseRef-") and not (
            record["license_evidence"] or record.get("license_source")
        ):
            raise Refusal(
                Finding(
                    "dependency.licence_source",
                    "dependency-provenance.json",
                    "Custom licence identity needs exact source text provenance.",
                )
            )
    return source, records
