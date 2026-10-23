# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — actual package graph and native configuration tests

"""Exercise real installed producers, locked roles and actual hook configurations."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from groundtruth_validation.dependencies import (
    validate_dependencies,
    verify_configuration,
    verify_installed,
    verify_records,
)
from groundtruth_validation.dependency_lock import parse_direct, parse_lock
from groundtruth_validation.dependency_records import read_provenance
from groundtruth_validation.report import Refusal
from groundtruth_validation.yaml_input import read_yaml

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture
def configuration(tmp_path: Path) -> Path:
    """Provide actual authored native configuration files for refusal inputs.

    Parameters
    ----------
    tmp_path : Path
        Per-test finite input directory.

    Returns
    -------
    Path
        Independent actual native configuration source bytes.
    """
    for relative in ("pyproject.toml", ".pre-commit-config.yaml", "mkdocs.yml"):
        (tmp_path / relative).write_bytes((REPOSITORY / relative).read_bytes())
    return tmp_path


def test_actual_complete_alignment_through_cli() -> None:
    """Reconcile real source, full installed graph and hooks through the public CLI."""
    result = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY / "tools/check_dependency_alignment.py"),
            "--root",
            str(REPOSITORY),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["reasons"] == []


def test_real_clean_environment_observation_and_refusal(tmp_path: Path) -> None:
    """Reinstall the actual complete hash lock with uv and reject altered observations."""
    for relative in (
        "repository-domain.json",
        "schemas/repository-domain.schema.json",
        "requirements-dev.txt",
        "requirements-dev.in",
        "dependency-provenance.json",
        "pyproject.toml",
        ".pre-commit-config.yaml",
        "mkdocs.yml",
        "Makefile",
        "native-tool-provenance.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPOSITORY / relative).read_bytes())
    for workflow in (REPOSITORY / ".github/workflows").glob("*.yml"):
        target = tmp_path / ".github/workflows" / workflow.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(workflow.read_bytes())
    for name in ("actionlint", "gitleaks"):
        native_relative = Path(".tool-cache/native") / name / name
        target = tmp_path / native_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.hardlink_to(REPOSITORY / native_relative)
    python = tmp_path / ".venv/bin/python"
    uv = str(REPOSITORY / ".venv/bin/uv")
    subprocess.run(
        [uv, "venv", "--python", sys.executable, str(tmp_path / ".venv")],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--offline",
            "--python",
            str(python),
            "--require-hashes",
            "--link-mode",
            "hardlink",
            "--default-index",
            "https://pypi.org/simple",
            "--build-constraints",
            str(tmp_path / "requirements-dev.txt"),
            "-r",
            str(tmp_path / "requirements-dev.txt"),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    arguments = [
        str(python),
        str(REPOSITORY / "tools/check_dependency_alignment.py"),
        "--root",
        str(tmp_path),
        "--json",
    ]
    baseline = subprocess.run(arguments, capture_output=True, text=True, check=False, timeout=15)
    assert baseline.returncode == 0, baseline.stdout
    observation = tmp_path / "dependency-provenance.json"
    data = json.loads(observation.read_text())
    data["lock_sha256"] = "0" * 64
    observation.write_text(json.dumps(data))
    mismatched = subprocess.run(arguments, capture_output=True, text=True, check=False, timeout=15)
    assert mismatched.returncode == 2
    assert json.loads(mismatched.stdout)["reasons"][0]["code"] == "dependency.observation"
    observation.write_text("{}")
    malformed = subprocess.run(arguments, capture_output=True, text=True, check=False, timeout=15)
    assert malformed.returncode == 2
    assert json.loads(malformed.stdout)["reasons"][0]["code"] == "dependency.records"


def test_unaccepted_metadata_and_foreign_environment(repository: Path) -> None:
    """Refuse missing metadata and an input tree without this actual environment."""
    assert validate_dependencies(repository / "missing").exit_code != 0
    report = validate_dependencies(repository)
    assert report.exit_code == 3
    assert report.findings[0].code == "installed.environment"


def test_actual_installed_producer_mismatches() -> None:
    """Compare altered observations with real packages, without mutating the environment."""
    _, records = read_provenance(REPOSITORY)
    assert verify_installed(records) == []
    changed = copy.deepcopy(records)
    changed[0]["version"] = "0.0.0"
    changed[0]["installer"] = "different-producer"
    assert {item.code for item in verify_installed(changed)} == {
        "installed.identity",
        "installed.installer",
    }
    changed[0]["name"] = "missing-actual-package"
    assert "installed.population" in {item.code for item in verify_installed(changed)}


@pytest.mark.parametrize("fault", ["population", "version", "producer", "artifact", "direct"])
def test_lock_record_and_role_refusals(fault: str) -> None:
    """Refuse real source observations altered away from the exact lock and roles."""
    _, records = read_provenance(REPOSITORY)
    lock = parse_lock((REPOSITORY / "requirements-dev.txt").read_bytes())
    direct = parse_direct((REPOSITORY / "requirements-dev.in").read_bytes())
    assert verify_records(records, lock, direct) == []
    if fault == "population":
        records[0]["name"] = "missing-locked-package"
        expected = "dependency.population"
    elif fault == "version":
        records[0]["version"] = "0.0.0"
        expected = "dependency.version"
    elif fault == "producer":
        records[0]["metadata_source"] = "https://example.invalid/CONFIDENTIAL_PAYLOAD"
        expected = "dependency.producer"
    elif fault == "artifact":
        records[0]["allowed_artifacts"][0]["sha256"] = "0" * 64
        expected = "dependency.artifact"
    else:
        direct["ruff"] = "0.0.0"
        expected = "dependency.version"
    findings = verify_records(records, lock, direct)
    assert expected in {item.code for item in findings}
    assert all("CONFIDENTIAL_PAYLOAD" not in item.message for item in findings)


@pytest.mark.parametrize("content", ["[broken", 'tool = "not a mapping"'])
def test_invalid_native_configuration(configuration: Path, content: str) -> None:
    """Keep malformed TOML and invalid nested types as authored configuration failures."""
    (configuration / "pyproject.toml").write_text(content)
    with pytest.raises(Refusal) as caught:
        verify_configuration(configuration, {"pre-commit": "4.7.0"})
    assert caught.value.finding.code == "dependency.configuration"


def test_strict_runtime_and_renderer_invariants(configuration: Path) -> None:
    """Refuse a declared unavailable runtime and weakened strict renderer settings."""
    project = configuration / "pyproject.toml"
    project.write_text(project.read_text() + '\n[project]\nname = "unavailable-runtime"\n')
    docs = read_yaml(configuration, "mkdocs.yml")
    docs["strict"] = "false"
    (configuration / "mkdocs.yml").write_text(json.dumps(docs))
    codes = {item.code for item in verify_configuration(configuration, {"pre-commit": "0.0.0"})}
    assert codes >= {"dependency.runtime", "dependency.renderer", "dependency.hook_version"}


@pytest.mark.parametrize("fault", ["repo", "entries", "entry", "command", "population"])
def test_native_hook_refusals(configuration: Path, fault: str) -> None:
    """Reject foreign sources, missing declarations, extra dependencies and command drift."""
    hooks = read_yaml(configuration, ".pre-commit-config.yaml")
    repos = hooks["repos"]
    assert isinstance(repos, list)
    repo = repos[0]
    assert isinstance(repo, dict)
    if fault == "repo":
        repo["repo"] = "https://example.invalid/hook-source"
        expected = "dependency.hook_source"
    elif fault == "entries":
        repo["hooks"] = "missing"
        expected = "dependency.hook_shape"
    else:
        entries = repo["hooks"]
        assert isinstance(entries, list)
        if fault == "entry":
            entries[0] = "invalid"
            expected = "dependency.hook_shape"
        elif fault == "command":
            entries[0]["entry"] = "unlocked-command"
            expected = "dependency.hook_entry"
        else:
            entries.pop()
            expected = "dependency.hook_population"
    (configuration / ".pre-commit-config.yaml").write_text(json.dumps(hooks))
    try:
        findings = verify_configuration(configuration, {"pre-commit": "4.7.0"})
    except Refusal as problem:
        assert problem.finding.code == expected
    else:
        assert expected in {item.code for item in findings}
