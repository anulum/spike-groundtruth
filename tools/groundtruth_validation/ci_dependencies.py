# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — workflow interpreter and native prerequisite alignment

"""Reconcile actual workflow tool versions and prerequisites with the local graph."""

import platform
from pathlib import Path

from groundtruth_validation.report import Finding, Refusal
from groundtruth_validation.yaml_input import read_yaml


def verify_ci_dependencies(root: Path, direct: dict[str, str]) -> list[Finding]:
    """Inspect real workflow steps for locked interpreters and native prerequisites.

    Parameters
    ----------
    root : Path
        Repository containing the actual distributed workflows.
    direct : dict[str, str]
        Exact direct development tool versions.

    Returns
    -------
    list[Finding]
        Actual version or prerequisite mismatches; preparation is not a hosted pass.

    Raises
    ------
    Refusal
        A required workflow configuration is unavailable or invalid.
    """
    findings: list[Finding] = []
    paths = sorted((root / ".github/workflows").glob("*.yml"))
    if not paths:
        return [
            Finding(
                "ci.unavailable",
                ".github/workflows",
                "Actual workflow dependency declarations are unavailable.",
                3,
            )
        ]
    for path in paths:
        relative = path.relative_to(root).as_posix()
        workflow = read_yaml(root, relative)
        jobs = workflow.get("jobs")
        if not isinstance(jobs, dict):
            raise Refusal(Finding("ci.shape", relative, "Workflow job mapping is invalid.", 4))
        for job in jobs.values():
            if not isinstance(job, dict):
                raise Refusal(
                    Finding("ci.shape", relative, "Workflow job declaration is invalid.", 4)
                )
            steps = job.get("steps", [])
            if not isinstance(steps, list):
                raise Refusal(
                    Finding("ci.shape", relative, "Workflow native step sequence is invalid.", 4)
                )
            native_ready = False
            for step in steps:
                if not isinstance(step, dict):
                    raise Refusal(
                        Finding(
                            "ci.shape", relative, "Workflow native step declaration is invalid.", 4
                        )
                    )
                action = step.get("uses", "")
                inputs = step.get("with", {})
                if not isinstance(action, str) or not isinstance(inputs, dict):
                    raise Refusal(
                        Finding("ci.shape", relative, "Workflow action declaration is invalid.", 4)
                    )
                if (
                    action.startswith("actions/setup-python@")
                    and inputs.get("python-version") != platform.python_version()
                ):
                    findings.append(
                        Finding(
                            "ci.python",
                            relative,
                            "Workflow Python differs from the actual qualified interpreter.",
                        )
                    )
                if action.startswith("astral-sh/setup-uv@") and inputs.get("version") != direct.get(
                    "uv"
                ):
                    findings.append(
                        Finding(
                            "ci.uv",
                            relative,
                            "Workflow bootstrap differs from the exact locked uv tool.",
                        )
                    )
                command = step.get("run", "")
                if not isinstance(command, str):
                    raise Refusal(
                        Finding("ci.shape", relative, "Workflow command must be literal text.", 4)
                    )
                if command.strip() == "make native-tools":
                    native_ready = True
                if (
                    any(
                        token in command
                        for token in (
                            "check_dependency_alignment.py",
                            "pre-commit run",
                            "pytest",
                            "native/actionlint",
                            "preflight.py",
                        )
                    )
                    and not native_ready
                ):
                    findings.append(
                        Finding(
                            "ci.native",
                            relative,
                            "Workflow consumes native validation before its exact prerequisite setup.",
                        )
                    )
    return findings
