# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — distributed workflow policy integration tests

"""Verify actual workflow inputs, action identities and aggregate semantics."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from groundtruth_validation.workflows import validate_workflows
from groundtruth_validation.yaml_input import read_yaml


def test_complete_workflow_configuration_through_cli(workflow_repository: Path) -> None:
    """Accept actual reviewed workflow preparation without claiming a hosted run."""
    command = Path(__file__).resolve().parents[1] / "tools/check_workflow_policy.py"
    result = subprocess.run(
        [sys.executable, str(command), "--root", str(workflow_repository), "--json"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["gate"] == "workflow_policy"
    assert json.loads(result.stdout)["reasons"] == []


@pytest.mark.parametrize(
    ("filename", "path", "value", "code"),
    [
        ("ci.yml", ("permissions",), {"contents": "write"}, "workflow.permissions"),
        ("ci.yml", ("on", "push", "paths"), ["src/**"], "workflow.triggers"),
        ("docs.yml", ("on",), {"pull_request_target": ""}, "workflow.triggers"),
        ("ci.yml", ("concurrency", "group"), "shared", "workflow.concurrency"),
        ("ci.yml", ("jobs", "required", "if"), "${{ success() }}", "workflow.aggregate"),
        ("ci.yml", ("jobs", "quality", "needs"), ["quality_main"], "workflow.aggregate"),
        ("ci.yml", ("jobs", "quality", "env", "RESULT_1"), "success", "workflow.aggregate"),
        ("ci.yml", ("jobs", "quality", "steps", 0, "run"), "true\n", "workflow.aggregate"),
        ("ci.yml", ("jobs", "required", "steps", 0, "run"), "true\n", "workflow.aggregate"),
        (
            "ci.yml",
            ("jobs", "quality_main", "steps", 5, "run"),
            ".venv/bin/ruff check tools\n",
            "workflow.composition",
        ),
        (
            "quality.yml",
            ("jobs", "hooks", "steps", 6, "run"),
            "make metadata\n",
            "workflow.composition",
        ),
        ("ci.yml", ("jobs", "quality", "uses"), "./.github/workflows/unknown.yml", "workflow.call"),
        ("ci.yml", ("jobs", "quality", "secrets"), "inherit", "workflow.call"),
        ("quality.yml", ("jobs", "quality", "timeout-minutes"), "999", "job.bounds"),
        (
            "quality.yml",
            ("jobs", "quality", "permissions"),
            {"contents": "write"},
            "job.permissions",
        ),
        ("quality.yml", ("jobs", "quality", "continue-on-error"), "true", "job.skip"),
        (
            "quality.yml",
            ("jobs", "quality", "steps", 0, "uses"),
            "actions/checkout@v7",
            "action.pin",
        ),
        ("quality.yml", ("jobs", "quality", "steps", 0, "uses"), {}, "action.pin"),
        (
            "quality.yml",
            ("jobs", "quality", "steps", 0, "uses"),
            "actions/checkout@" + "0" * 40,
            "action.provenance",
        ),
        (
            "quality.yml",
            ("jobs", "quality", "steps", 0, "with", "persist-credentials"),
            "true",
            "action.credentials",
        ),
        ("quality.yml", ("jobs", "quality", "steps", 1, "if"), "${{ false }}", "workflow.skip"),
        (
            "quality.yml",
            ("jobs", "quality", "steps", 1, "run"),
            "false || true",
            "workflow.authority",
        ),
        (
            "quality.yml",
            ("jobs", "quality", "steps", 1, "run"),
            "pip install pytest",
            "workflow.authority",
        ),
        ("quality.yml", ("jobs", "quality", "steps", 1, "run"), [], "workflow.command"),
        ("quality.yml", ("jobs", "quality", "steps"), [], "workflow.steps"),
        ("quality.yml", ("jobs", "quality", "steps", 0), "invalid", "workflow.shape"),
        (
            "codeql.yml",
            ("jobs", "analysis", "steps", 3, "with", "upload"),
            "always",
            "action.publication",
        ),
        (
            "ci.yml",
            ("jobs", "unexpected"),
            {"uses": "./.github/workflows/docs.yml"},
            "workflow.jobs",
        ),
        ("ci.yml", ("env",), {"VALUE": "${{ secrets.CONFIDENTIAL_PAYLOAD }}"}, "workflow.secrets"),
    ],
)
def test_actual_workflow_refusals(
    workflow_repository: Path, filename: str, path: tuple[str | int, ...], value: object, code: str
) -> None:
    """Reject altered real workflow semantics with located caller-safe findings."""
    relative = ".github/workflows/" + filename
    document = read_yaml(workflow_repository, relative)
    cursor: object = document
    for key in path[:-1]:
        if isinstance(key, int):
            assert isinstance(cursor, list)
            cursor = cursor[key]
        else:
            assert isinstance(cursor, dict)
            cursor = cursor[key]
    last = path[-1]
    if isinstance(last, int):
        assert isinstance(cursor, list)
        cursor[last] = value
    else:
        assert isinstance(cursor, dict)
        cursor[last] = value
    (workflow_repository / relative).write_text(json.dumps(document))
    report = validate_workflows(workflow_repository)
    assert report.exit_code != 0
    assert code in {item.code for item in report.findings}
    assert "CONFIDENTIAL_PAYLOAD" not in report.encode()


def test_inventory_policy_and_source_identity(workflow_repository: Path) -> None:
    """Reject unowned workflow files, missing files and weakened source policy."""
    extra = workflow_repository / ".github/workflows/unknown.yml"
    extra.write_bytes((workflow_repository / ".github/workflows/docs.yml").read_bytes())
    assert "workflow.inventory" in {
        item.code for item in validate_workflows(workflow_repository).findings
    }
    (workflow_repository / ".github/workflows/docs.yml").unlink()
    assert "file.unavailable" in {
        item.code for item in validate_workflows(workflow_repository).findings
    }
    (workflow_repository / "workflow-provenance.json").write_text("{}")
    assert validate_workflows(workflow_repository).findings[0].code == "workflow.sources"
    (workflow_repository / "workflow-policy.json").write_text("{}")
    assert validate_workflows(workflow_repository).findings[0].code == "workflow.policy"


def test_workflow_resource_bounds(workflow_repository: Path) -> None:
    """Refuse a real configuration exceeding the reviewed per-workflow size bound."""
    target = workflow_repository / ".github/workflows/docs.yml"
    target.write_bytes(target.read_bytes() + b"\n#" + b"x" * 102_400)
    assert "workflow.size" in {
        item.code for item in validate_workflows(workflow_repository).findings
    }
