# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — actual CI interpreter and prerequisite tests

"""Exercise actual workflow inputs and reject tool version or prerequisite drift."""

import json
from pathlib import Path

import pytest

from groundtruth_validation.ci_dependencies import verify_ci_dependencies
from groundtruth_validation.report import Refusal
from groundtruth_validation.yaml_input import read_yaml


def test_actual_ci_alignment_and_missing_inputs(workflow_repository: Path) -> None:
    """Accept current real workflows and refuse an absent declaration directory."""
    assert verify_ci_dependencies(workflow_repository, {"uv": "0.13.4"}) == []
    assert verify_ci_dependencies(workflow_repository / "missing", {})[0].exit_code == 3


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ({"jobs": []}, "ci.shape"),
        ({"jobs": {"job": []}}, "ci.shape"),
        ({"jobs": {"job": {"steps": {}}}}, "ci.shape"),
        ({"jobs": {"job": {"steps": ["invalid"]}}}, "ci.shape"),
        ({"jobs": {"job": {"steps": [{"uses": []}]}}}, "ci.shape"),
        ({"jobs": {"job": {"steps": [{"with": []}]}}}, "ci.shape"),
        ({"jobs": {"job": {"steps": [{"run": []}]}}}, "ci.shape"),
    ],
)
def test_malformed_ci_inputs(workflow_repository: Path, value: object, code: str) -> None:
    """Refuse finite malformed source inputs before interpreting their commands."""
    target = workflow_repository / ".github/workflows/ci.yml"
    target.write_text(json.dumps(value))
    with pytest.raises(Refusal) as caught:
        verify_ci_dependencies(workflow_repository, {"uv": "0.13.4"})
    assert caught.value.finding.code == code
    assert caught.value.finding.exit_code == 4


def test_actual_ci_version_and_prerequisite_drift(workflow_repository: Path) -> None:
    """Reject changed actual interpreter, bootstrap and prerequisite ordering."""
    relative = ".github/workflows/quality.yml"
    document = read_yaml(workflow_repository, relative)
    jobs = document["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["quality"]
    assert isinstance(job, dict)
    steps = job["steps"]
    assert isinstance(steps, list)
    for step in steps:
        assert isinstance(step, dict)
        inputs = step.get("with", {})
        assert isinstance(inputs, dict)
        if "python-version" in inputs:
            inputs["python-version"] = "0.0.0"
        if "version" in inputs:
            inputs["version"] = "0.0.0"
        if step.get("run") == "make native-tools":
            step["run"] = "make metadata"
    (workflow_repository / relative).write_text(json.dumps(document))
    assert {
        item.code for item in verify_ci_dependencies(workflow_repository, {"uv": "0.13.4"})
    } == {"ci.python", "ci.uv", "ci.native"}
