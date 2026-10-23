# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — actual bounded preflight outcomes

"""Aggregate real tool exits and strict checker reports without invented passes."""

import importlib.util
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from groundtruth_validation.execution import run_tool
from groundtruth_validation.inputs import parse_json, read_file
from groundtruth_validation.provenance import ASSET_SHA256
from groundtruth_validation.report import Finding, Refusal, Report
from groundtruth_validation.structure import maintained_paths

STATUSES = {0: "pass", 2: "refused", 3: "unavailable", 4: "invalid"}


@dataclass(frozen=True)
class Check:
    """Declare a fixed authored check, never an artifact-selected executable.

    Parameters
    ----------
    name : str
        Stable authored check name.
    arguments : tuple[str, ...]
        Literal tool vector starting with its absolute executable.
    location : str
        Authored repository-relative diagnostic location.
    timeout : float
        Finite wall-clock deadline in seconds.
    gate : str or None
        Required structured checker gate; None for a native exit-code tool.
    module : str or None
        Required locked Python module for native module tools.
    source_stdin : bool
        Send the actual finite maintained text cohort to the secret scanner.
    """

    name: str
    arguments: tuple[str, ...]
    location: str
    timeout: float
    gate: str | None = None
    module: str | None = None
    source_stdin: bool = False


@dataclass(frozen=True)
class Outcome:
    """Record an actual check result without echoing native diagnostics.

    Parameters
    ----------
    name : str
        Authored check name.
    status : str
        Observed pass, refused, unavailable or invalid state.
    returncode : int or None
        Actual observed child exit; None when no exit was observed.
    reason_codes : tuple[str, ...]
        Validated stable checker reason identifiers, without received text.
    """

    name: str
    status: str
    returncode: int | None
    reason_codes: tuple[str, ...] = ()


@dataclass
class PreflightReport(Report):
    """Retain every actual requested check outcome alongside scoped findings.

    Parameters
    ----------
    gate : str
        Full preflight or explicitly scoped preflight operation name.
    findings : list[Finding]
        Every observed check failure.
    checks : list[Outcome]
        Actual ordered outcomes, never inferred from a missing report.
    """

    checks: list[Outcome] = field(default_factory=list)

    def encode(self) -> str:
        """Return deterministic scoped JSON including actual exits and reason codes."""
        data = parse_json(super().encode().encode("utf-8"), ".")
        data["checks"] = [
            {
                "name": item.name,
                "status": item.status,
                "returncode": item.returncode,
                "reason_codes": list(item.reason_codes),
            }
            for item in self.checks
        ]
        return json.dumps(data, ensure_ascii=True, sort_keys=True) + "\n"


def source_payload(root: Path) -> bytes:
    """Read the actual maintained text cohort within an eight MiB total budget.

    Parameters
    ----------
    root : Path
        Actual standalone repository root.

    Returns
    -------
    bytes
        Source text separated by newlines, excluding exact licensed binary assets.

    Raises
    ------
    Refusal
        Inventory, source input or aggregate byte budget is unavailable or invalid.
    """
    parts: list[bytes] = []
    total = 0
    for relative in maintained_paths(root):
        if relative in ASSET_SHA256:
            continue
        content = read_file(root, relative)
        total += len(content) + 1
        if total > 8_388_608:
            raise Refusal(
                Finding(
                    "source.budget", ".", "Maintained source exceeds the secret-scan input budget."
                )
            )
        parts.append(content)
    if not parts:
        raise Refusal(
            Finding("source.empty", ".", "Secret scanning requires actual maintained source.")
        )
    return b"\n".join(parts)


def validate_checker_report(
    data: dict[str, object], check: Check, returncode: int
) -> tuple[str, ...]:
    """Validate the exact child protocol before retaining reason identifiers.

    Parameters
    ----------
    data : dict[str, object]
        Actual strict parsed child output or a diagnostic protocol input.
    check : Check
        Authored expected checker identity and safe locating path.
    returncode : int
        Actual independently observed child exit.

    Returns
    -------
    tuple[str, ...]
        Stable reason identifiers without received diagnostic text.

    Raises
    ------
    Refusal
        Gate, scope, exit, status or diagnostic fields contradict the protocol.
    """
    reasons = data.get("reasons")
    if (
        set(data) != {"gate", "scope", "status", "reasons"}
        or data.get("gate") != check.gate
        or data.get("scope") != "local_scaffold_infrastructure"
        or returncode not in STATUSES
        or data.get("status") != STATUSES[returncode]
        or not isinstance(reasons, list)
        or bool(reasons) != (returncode != 0)
    ):
        raise Refusal(
            Finding(
                "check.protocol",
                check.location,
                "Required checker returned an invalid scoped result.",
                4,
            ),
            returncode=returncode,
        )
    codes: list[str] = []
    for reason in reasons:
        if (
            not isinstance(reason, dict)
            or set(reason) != {"code", "path", "message"}
            or not all(isinstance(value, str) for value in reason.values())
            or not re.fullmatch(r"[a-z][a-z0-9_.-]{0,79}", reason["code"])
        ):
            raise Refusal(
                Finding(
                    "check.protocol",
                    check.location,
                    "Required checker returned invalid reason fields.",
                    4,
                ),
                returncode=returncode,
            )
        codes.append(reason["code"])
    return tuple(codes)


def run_check(root: Path, check: Check) -> tuple[Outcome, list[Finding]]:
    """Execute one real check and preserve its actual exit and report meaning.

    Parameters
    ----------
    root : Path
        Actual child working directory.
    check : Check
        Fixed authored tool declaration; received artifacts never select it.

    Returns
    -------
    tuple[Outcome, list[Finding]]
        Actual observation and safe failures. Native diagnostic text is not echoed.
    """
    returncode: int | None = None
    try:
        if check.module is not None and importlib.util.find_spec(check.module) is None:
            raise Refusal(
                Finding(
                    "check.module", check.location, "Required locked Python tool is unavailable.", 3
                )
            )
        payload = source_payload(root) if check.source_stdin else None
        result = run_tool(check.arguments, root=root, timeout=check.timeout, payload=payload)
        returncode = result.returncode
        codes: tuple[str, ...] = ()
        if check.gate is not None:
            try:
                data = parse_json(result.stdout, check.location)
            except Refusal as exc:
                raise Refusal(
                    Finding(
                        "check.report",
                        check.location,
                        "Required checker did not return strict JSON.",
                        4,
                    ),
                    returncode=returncode,
                ) from exc
            codes = validate_checker_report(data, check, returncode)
        exit_code = returncode if check.gate is not None else 0 if returncode == 0 else 2
        outcome = Outcome(check.name, STATUSES[exit_code], returncode, codes)
        findings = (
            []
            if exit_code == 0
            else [
                Finding(
                    "check.failed",
                    check.location,
                    "Required check reported a failed outcome.",
                    exit_code,
                )
            ]
        )
        return outcome, findings
    except Refusal as exc:
        observed = exc.returncode if exc.returncode is not None else returncode
        return Outcome(check.name, STATUSES[exc.finding.exit_code], observed), [exc.finding]


def run_checks(root: Path, checks: tuple[Check, ...], *, complete: bool = False) -> PreflightReport:
    """Aggregate the actual declared sequence without short-circuiting failures.

    Parameters
    ----------
    root : Path
        Actual repository and tool working directory.
    checks : tuple[Check, ...]
        Fixed required sequence for this explicitly selected operation.
    complete : bool
        True only for the entire compiled local-scaffold profile.

    Returns
    -------
    PreflightReport
        Every actual outcome with 4, then 3, then 2 failure precedence.
    """
    report = PreflightReport("preflight" if complete else "preflight_scoped", [])
    if complete:
        from groundtruth_validation.validation_profile import scaffold_checks

        if checks != scaffold_checks(root):
            report.findings.append(
                Finding(
                    "preflight.profile",
                    ".",
                    "Full preflight requires the entire fixed execution profile.",
                    4,
                )
            )
            return report
    if not checks or len({item.name for item in checks}) != len(checks):
        report.findings.append(
            Finding(
                "preflight.selection",
                ".",
                "Required checks must form a nonempty unique sequence.",
                4,
            )
        )
        return report
    for check in checks:
        outcome, findings = run_check(root, check)
        report.checks.append(outcome)
        report.findings.extend(findings)
    return report
