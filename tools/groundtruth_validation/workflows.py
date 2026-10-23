# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — distributed workflow policy acceptance

"""Bind every actual workflow job to reviewed source and read-only policy."""

import hashlib
import re
from pathlib import Path
from typing import cast

from groundtruth_validation.inputs import read_file, read_json
from groundtruth_validation.report import Finding, Refusal, Report
from groundtruth_validation.yaml_input import read_yaml

POLICY_SHA256 = "9cfa881ab8dce593b59cfed590d2bdcc194c1ff6a068e0ef089ffe7d55bacfd2"


def _mapping(value: object) -> dict[str, object]:
    """Require a mapping before interpreting a workflow configuration node."""
    if not isinstance(value, dict):
        raise Refusal(
            Finding(
                "workflow.shape", ".github/workflows", "Workflow mapping is missing or invalid.", 4
            )
        )
    return {str(key): item for key, item in value.items()}


def _steps(
    job: dict[str, object], relative: str, action_pins: dict[str, str], findings: list[Finding]
) -> None:
    """Check actual native steps against independently bound action identities."""
    steps = job.get("steps")
    if not isinstance(steps, list) or not steps:
        raise Refusal(Finding("workflow.steps", relative, "Native job needs actual steps.", 4))
    for item in steps:
        step = _mapping(item)
        if "continue-on-error" in step or "if" in step:
            findings.append(
                Finding(
                    "workflow.skip", relative, "Required steps cannot be suppressed or conditional."
                )
            )
        action = step.get("uses")
        if action is not None:
            if not isinstance(action, str) or not re.fullmatch(
                r"[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}", action
            ):
                findings.append(
                    Finding(
                        "action.pin", relative, "Action requires an immutable full source commit."
                    )
                )
                continue
            source, commit = action.split("@")
            producer = "/".join(source.split("/")[:2])
            if action_pins.get(producer) != commit:
                findings.append(
                    Finding(
                        "action.provenance",
                        relative,
                        "Action differs from the verified producer source.",
                    )
                )
            inputs = _mapping(step.get("with", {}))
            if producer == "actions/checkout" and inputs.get("persist-credentials") != "false":
                findings.append(
                    Finding(
                        "action.credentials",
                        relative,
                        "Checkout must disable credential persistence.",
                    )
                )
            if source == "github/codeql-action/analyze" and (
                inputs.get("upload") != "never" or inputs.get("upload-database") != "false"
            ):
                findings.append(
                    Finding(
                        "action.publication", relative, "CodeQL analysis must disable all uploads."
                    )
                )
        command = step.get("run")
        if command is not None:
            if not isinstance(command, str):
                raise Refusal(
                    Finding("workflow.command", relative, "Step command must be literal text.", 4)
                )
            if re.search(r"(?m)^\s*(?:python(?:3)? -m )?pip install\b", command) or any(
                token in command
                for token in ("|| true", "git push", "gh release", "twine", "deploy")
            ):
                findings.append(
                    Finding(
                        "workflow.authority",
                        relative,
                        "Command suppresses failures or exceeds local analysis authority.",
                    )
                )


def _aggregate(
    job: dict[str, object],
    children: list[str],
    environment: dict[str, str],
    findings: list[Finding],
) -> None:
    """Require every actual descendant result with exact non-suppressing commands."""
    steps = job.get("steps")
    commands = "\n".join('test "$' + key + '" = success' for key in environment) + "\n"
    if (
        job.get("needs") != children
        or job.get("if") != "${{ always() }}"
        or job.get("env") != environment
        or not isinstance(steps, list)
        or len(steps) != 1
        or not isinstance(steps[0], dict)
        or steps[0].get("run") != commands
    ):
        findings.append(
            Finding(
                "workflow.aggregate",
                ".github/workflows/ci.yml",
                "Aggregate must require every complete actual descendant outcome.",
            )
        )


def _composition(
    root: Path,
    filename: str,
    jobs: dict[str, object],
    policy: dict[str, object],
    findings: list[Finding],
) -> None:
    """Bind real expanded jobs to original leaves and all category result gates."""
    for row in cast(list[dict[str, str]], policy["composed_jobs"]):
        if row["workflow"] != filename:
            continue
        source = read_yaml(root, ".github/workflows/" + row["source_workflow"])
        source_jobs = _mapping(source.get("jobs"))
        if jobs.get(row["job"]) != source_jobs.get(row["source_job"]):
            findings.append(
                Finding(
                    "workflow.composition",
                    ".github/workflows/" + filename,
                    "Expanded execution differs from its complete source job.",
                )
            )
    if filename != "ci.yml":
        return
    for category, children in cast(dict[str, list[str]], policy["category_members"]).items():
        environment = {
            "RESULT_" + str(i): "${{ needs." + child + ".result }}"
            for i, child in enumerate(children)
        }
        _aggregate(_mapping(jobs.get(category)), children, environment, findings)
    categories = cast(dict[str, int], policy["required_categories"])
    environment = {
        category.upper() + "_RESULT": "${{ needs." + category + ".result }}"
        for category in categories
    }
    _aggregate(_mapping(jobs.get("required")), list(categories), environment, findings)


def validate_workflows(root: Path) -> Report:
    """Validate every distributed job, trigger, action pin and aggregate outcome.

    Parameters
    ----------
    root : Path
        Repository containing its reviewed workflow inventory and action sources.

    Returns
    -------
    Report
        Static workflow preparation result, never a hosted execution claim.
    """
    report = Report("workflow_policy", [])
    try:
        policy, raw = read_json(root, "workflow-policy.json")
        if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
            raise Refusal(
                Finding(
                    "workflow.policy",
                    "workflow-policy.json",
                    "Workflow policy differs from reviewed source.",
                    4,
                )
            )
        provenance, raw_provenance = read_json(root, "workflow-provenance.json")
        if hashlib.sha256(raw_provenance).hexdigest() != policy["provenance_sha256"]:
            raise Refusal(
                Finding(
                    "workflow.sources",
                    "workflow-provenance.json",
                    "Action provenance differs from reviewed source.",
                    4,
                )
            )
        # Exact reviewed JSON identities establish these configuration types.
        pins = {
            row["repository"]: row["commit"]
            for row in cast(list[dict[str, str]], provenance["actions"])
        }
        hashes = cast(dict[str, str], policy["workflow_sha256"])
        declared = cast(list[dict[str, object]], policy["jobs"])
        aggregate_names = {"required", *cast(dict[str, int], policy["required_categories"])}
        actual_names = {p.name for p in (root / ".github/workflows").glob("*")}
        if actual_names != set(hashes):
            report.findings.append(
                Finding(
                    "workflow.inventory",
                    ".github/workflows",
                    "Actual workflow files differ from the complete declared inventory.",
                )
            )
        for name in sorted(hashes):
            relative = ".github/workflows/" + name
            try:
                content = read_file(root, relative)
                if len(content) > 102_400 or len(content.splitlines()) > 1000:
                    report.findings.append(
                        Finding(
                            "workflow.size",
                            relative,
                            "Workflow exceeds its reviewed local resource bounds.",
                        )
                    )
                if hashlib.sha256(content).hexdigest() != hashes[name]:
                    report.findings.append(
                        Finding(
                            "workflow.identity",
                            relative,
                            "Workflow bytes differ from their reviewed inventory.",
                        )
                    )
                if b"secrets." in content:
                    report.findings.append(
                        Finding(
                            "workflow.secrets",
                            relative,
                            "Local analysis cannot require repository secrets.",
                        )
                    )
                workflow = read_yaml(root, relative)
                if workflow.get("permissions") != {"contents": "read"}:
                    report.findings.append(
                        Finding(
                            "workflow.permissions",
                            relative,
                            "Workflow permissions must be contents read only.",
                        )
                    )
                trigger = _mapping(workflow.get("on"))
                if name == "ci.yml":
                    if (
                        set(trigger) != {"push", "pull_request"}
                        or trigger.get("push") != {"branches": ["main"]}
                        or trigger.get("pull_request") not in ("", {})
                    ):
                        report.findings.append(
                            Finding(
                                "workflow.triggers",
                                relative,
                                "Coordinator must cover every main push and pull request without path filters.",
                            )
                        )
                elif trigger != {"workflow_call": ""}:
                    report.findings.append(
                        Finding(
                            "workflow.triggers",
                            relative,
                            "Reusable workflow must expose only its intended empty call surface.",
                        )
                    )
                concurrency = _mapping(workflow.get("concurrency"))
                if (
                    concurrency.get("group")
                    != "groundtruth-" + Path(name).stem + "-${{ github.ref }}"
                    or concurrency.get("cancel-in-progress") != "true"
                ):
                    report.findings.append(
                        Finding(
                            "workflow.concurrency",
                            relative,
                            "Workflow needs its own bounded concurrency group.",
                        )
                    )
                jobs = _mapping(workflow.get("jobs"))
                expected_jobs = {str(row["job"]) for row in declared if row["workflow"] == name}
                expected_kinds = {
                    str(row["job"]): row["kind"] for row in declared if row["workflow"] == name
                }
                if set(jobs) != expected_jobs:
                    report.findings.append(
                        Finding(
                            "workflow.jobs",
                            relative,
                            "Each actual job must have exactly one declared owner and category.",
                        )
                    )
                for job_name, value in jobs.items():
                    job = _mapping(value)
                    if "permissions" in job and job["permissions"] != {"contents": "read"}:
                        report.findings.append(
                            Finding(
                                "job.permissions",
                                relative,
                                "Job cannot escalate workflow permissions.",
                            )
                        )
                    if "continue-on-error" in job or (
                        "if" in job and not (name == "ci.yml" and job_name in aggregate_names)
                    ):
                        report.findings.append(
                            Finding(
                                "job.skip",
                                relative,
                                "Required job cannot be suppressed or conditional.",
                            )
                        )
                    reusable = job.get("uses")
                    actual_kind = (
                        "reusable"
                        if reusable is not None
                        else "aggregate"
                        if name == "ci.yml" and job_name in aggregate_names
                        else "native"
                    )
                    if expected_kinds.get(job_name) != actual_kind:
                        report.findings.append(
                            Finding(
                                "workflow.kind",
                                relative,
                                "Job implementation differs from its declared responsibility.",
                            )
                        )
                    if reusable is not None or "secrets" in job:
                        report.findings.append(
                            Finding(
                                "workflow.call",
                                relative,
                                "Selected native composition cannot call workflows or inherit secrets.",
                            )
                        )
                        continue
                    timeout = job.get("timeout-minutes")
                    if (
                        job.get("runs-on") != "ubuntu-24.04"
                        or not isinstance(timeout, str)
                        or not timeout.isdecimal()
                        or not 1 <= int(timeout) <= 15
                    ):
                        report.findings.append(
                            Finding(
                                "job.bounds",
                                relative,
                                "Native job needs the reviewed runner and a finite timeout.",
                            )
                        )
                    _steps(job, relative, pins, report.findings)
                _composition(root, name, jobs, policy, report.findings)
            except Refusal as exc:
                report.findings.append(exc.finding)
    except Refusal as exc:
        report.findings.append(exc.finding)
    return report
