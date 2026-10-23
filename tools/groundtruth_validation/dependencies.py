# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — actual locked development graph alignment

"""Reconcile direct inputs, complete locks, observed packages, hooks and CI."""

import hashlib
import platform
import sys
import sysconfig
import tomllib
from importlib.metadata import Distribution, distributions
from pathlib import Path

from groundtruth_validation.ci_dependencies import verify_ci_dependencies
from groundtruth_validation.dependency_lock import parse_direct, parse_lock
from groundtruth_validation.dependency_records import PackageRecord, read_provenance
from groundtruth_validation.inputs import read_file
from groundtruth_validation.metadata import validate_metadata
from groundtruth_validation.native_tools import verify_native_tools
from groundtruth_validation.report import Finding, Refusal, Report
from groundtruth_validation.yaml_input import read_yaml

HOOK_ENTRIES = {
    "ruff": ".venv/bin/python -m ruff check",
    "ruff-format": ".venv/bin/python -m ruff format --check",
    "strict-types": ".venv/bin/python -m mypy --strict tools tests",
    "metadata": ".venv/bin/python tools/check_repository_metadata.py --root . --json",
    "source-provenance": ".venv/bin/python tools/check_source_provenance.py --root . --json",
    "workflow-policy": ".venv/bin/python tools/check_workflow_policy.py --root . --json",
    "dependency-alignment": ".venv/bin/python tools/check_dependency_alignment.py --root . --json",
    "documentation": ".venv/bin/python tools/check_documentation.py --root . --json",
    "repository-inventory": ".venv/bin/python tools/check_repository_inventory.py --root . --json",
    "reuse": ".venv/bin/python -m reuse lint",
}


def verify_installed(records: list[PackageRecord]) -> list[Finding]:
    """Compare declared observations with the actual complete installed producer set.

    Parameters
    ----------
    records : list[PackageRecord]
        Closed and validated package observations.

    Returns
    -------
    list[Finding]
        Actual graph, version, producer and metadata mismatches. Recorded install
        RECORD hashes remain observations, since installed script paths vary.
    """
    from packaging.utils import canonicalize_name

    findings: list[Finding] = []
    actual: dict[str, Distribution] = {
        canonicalize_name(item.metadata.get("Name", "")): item for item in distributions()
    }
    if set(actual) != {item["name"] for item in records}:
        findings.append(
            Finding(
                "installed.population",
                ".venv",
                "Actual installed package population differs from the complete record.",
                3,
            )
        )
    for record in records:
        installed = actual.get(record["name"])
        if installed is None:
            continue
        metadata = installed.read_text("METADATA")
        if (
            installed.version != record["version"]
            or metadata is None
            or hashlib.sha256(metadata.encode()).hexdigest() != record["metadata_sha256"]
        ):
            findings.append(
                Finding(
                    "installed.identity",
                    ".venv",
                    "Installed version or producer metadata differs from its source observation.",
                    3,
                )
            )
        if (installed.read_text("INSTALLER") or "").strip() != record["installer"]:
            findings.append(
                Finding(
                    "installed.installer",
                    ".venv",
                    "Installed producer differs from its exact recorded installation source.",
                    3,
                )
            )
    return findings


def verify_records(
    records: list[PackageRecord],
    lock: dict[str, tuple[str, frozenset[str]]],
    direct: dict[str, str],
) -> list[Finding]:
    """Reconcile every recorded version, role and release artifact with the lock.

    Parameters
    ----------
    records : list[PackageRecord]
        Complete validated observation records.
    lock : dict[str, tuple[str, frozenset[str]]]
        Exact package versions and allowed SHA-256 hashes.
    direct : dict[str, str]
        Exact direct development requirements.

    Returns
    -------
    list[Finding]
        Located mismatches without echoing source values or download URLs.
    """
    findings: list[Finding] = []
    if {row["name"] for row in records} != set(lock) or not set(direct).issubset(lock):
        findings.append(
            Finding(
                "dependency.population",
                "dependency-provenance.json",
                "Lock, direct inputs and provenance populations differ.",
            )
        )
    for record in records:
        name = record["name"]
        entry = lock.get(name)
        if entry is None:
            continue
        version, hashes = entry
        expected_role = (
            "direct development tool" if name in direct else "transitive development dependency"
        )
        if (
            record["version"] != version
            or (name in direct and direct[name] != version)
            or record["role"] != expected_role
        ):
            findings.append(
                Finding(
                    "dependency.version",
                    "dependency-provenance.json",
                    "Recorded version or role differs from exact lock inputs.",
                )
            )
        if (
            record["metadata_source"] != f"https://pypi.org/pypi/{name}/{version}/json"
            or record["installer"] != "uv"
        ):
            findings.append(
                Finding(
                    "dependency.producer",
                    "dependency-provenance.json",
                    "Package source or installer identity differs from the approved producer.",
                )
            )
        if any(
            a["sha256"] not in hashes
            or not a["url"].startswith("https://files.pythonhosted.org/packages/")
            or "/" in a["filename"]
            for a in record["allowed_artifacts"]
        ):
            findings.append(
                Finding(
                    "dependency.artifact",
                    "dependency-provenance.json",
                    "Release artifact does not match the hash lock and primary distribution source.",
                )
            )
    return findings


def _mapping(value: object) -> dict[str, object]:
    """Require native mapping shape before inspecting nested tool configuration."""
    if not isinstance(value, dict):
        raise Refusal(
            Finding(
                "dependency.configuration",
                "pyproject.toml",
                "Native tool settings must be TOML mappings.",
                4,
            )
        )
    return {str(key): item for key, item in value.items()}


def verify_configuration(root: Path, direct: dict[str, str]) -> list[Finding]:
    """Check actual native tooling, local hook entries and the configured renderer.

    Parameters
    ----------
    root : Path
        Explicit repository directory.
    direct : dict[str, str]
        Exact tool versions from the authored direct requirements.

    Returns
    -------
    list[Finding]
        Native configuration and isolated hook mismatches.

    Raises
    ------
    Refusal
        Configuration is unavailable or cannot be parsed safely.
    """
    findings: list[Finding] = []
    try:
        project = tomllib.loads(read_file(root, "pyproject.toml").decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise Refusal(
            Finding(
                "dependency.configuration",
                "pyproject.toml",
                "Native Python configuration is invalid.",
                4,
            )
        ) from exc
    tool = _mapping(project.get("tool", {}))
    mypy = _mapping(tool.get("mypy", {}))
    ruff = _mapping(tool.get("ruff", {}))
    lint = _mapping(ruff.get("lint", {}))
    style = _mapping(lint.get("pydocstyle", {}))
    if (
        "project" in project
        or "build-system" in project
        or mypy.get("strict") is not True
        or style.get("convention") != "numpy"
    ):
        findings.append(
            Finding(
                "dependency.runtime",
                "pyproject.toml",
                "Initial tooling must retain strict native checks without an unavailable runtime distribution.",
            )
        )
    hooks = read_yaml(root, ".pre-commit-config.yaml")
    if hooks.get("minimum_pre_commit_version") != direct.get("pre-commit"):
        findings.append(
            Finding(
                "dependency.hook_version",
                ".pre-commit-config.yaml",
                "Hook runner version differs from the exact development tool.",
            )
        )
    repos = hooks.get("repos")
    if (
        not isinstance(repos, list)
        or len(repos) != 1
        or not isinstance(repos[0], dict)
        or repos[0].get("repo") != "local"
    ):
        raise Refusal(
            Finding(
                "dependency.hook_source",
                ".pre-commit-config.yaml",
                "Hooks must use only the actual local locked environment.",
                4,
            )
        )
    entries = repos[0].get("hooks")
    if not isinstance(entries, list):
        raise Refusal(
            Finding(
                "dependency.hook_shape",
                ".pre-commit-config.yaml",
                "Actual native hook declarations are missing.",
                4,
            )
        )
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise Refusal(
                Finding(
                    "dependency.hook_shape",
                    ".pre-commit-config.yaml",
                    "Native hook declaration is invalid.",
                    4,
                )
            )
        identifier = entry["id"]
        if (
            identifier in seen
            or HOOK_ENTRIES.get(identifier) != entry.get("entry")
            or entry.get("language") != "system"
            or "additional_dependencies" in entry
        ):
            findings.append(
                Finding(
                    "dependency.hook_entry",
                    ".pre-commit-config.yaml",
                    "Hook command, source or dependency isolation differs from its reviewed native entry.",
                )
            )
        seen.add(identifier)
    if seen != set(HOOK_ENTRIES):
        findings.append(
            Finding(
                "dependency.hook_population",
                ".pre-commit-config.yaml",
                "Complete required native hook population differs.",
            )
        )
    docs = read_yaml(root, "mkdocs.yml")
    if (
        docs.get("docs_dir") != "docs"
        or docs.get("site_dir") != ".tool-cache/site"
        or docs.get("exclude_docs") != "internal/\n"
        or docs.get("strict") != "true"
    ):
        findings.append(
            Finding(
                "dependency.renderer",
                "mkdocs.yml",
                "Renderer must preserve strict source, private exclusion and owned output boundaries.",
            )
        )
    return findings


def validate_dependencies(root: Path) -> Report:
    """Run the complete actual development dependency alignment operation.

    Parameters
    ----------
    root : Path
        Repository with its own actual uv environment and complete hash lock.

    Returns
    -------
    Report
        Observed alignment findings; missing input, parser or package never passes.
    """
    metadata_report, metadata, _ = validate_metadata(root)
    report = Report("dependency_alignment", metadata_report.findings)
    if metadata is None:
        return report
    if (root / ".venv").is_symlink() or Path(sys.prefix).resolve() != (root / ".venv").resolve():
        report.findings.append(
            Finding(
                "installed.environment",
                ".venv",
                "Checker requires this repository's actual isolated environment.",
                3,
            )
        )
        return report
    try:
        raw_lock = read_file(root, "requirements-dev.txt")
        lock = parse_lock(raw_lock)
        direct = parse_direct(read_file(root, "requirements-dev.in"))
        source, records = read_provenance(root)
        if (
            source["lock_sha256"] != hashlib.sha256(raw_lock).hexdigest()
            or source["python_version"] != platform.python_version()
            or source["artifact_platform"] != sysconfig.get_platform()
        ):
            report.findings.append(
                Finding(
                    "dependency.observation",
                    "dependency-provenance.json",
                    "Recorded lock, interpreter or artifact platform differs from this actual environment.",
                )
            )
        report.findings.extend(verify_records(records, lock, direct))
        report.findings.extend(verify_installed(records))
        report.findings.extend(verify_configuration(root, direct))
        report.findings.extend(verify_native_tools(root))
        report.findings.extend(verify_ci_dependencies(root, direct))
    except Refusal as exc:
        report.findings.append(exc.finding)
    return report
