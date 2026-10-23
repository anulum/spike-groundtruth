# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — real preflight process and protocol tests

"""Exercise actual checker processes, native exits and strict report admission."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from groundtruth_validation.preflight import (
    Check,
    run_check,
    run_checks,
    source_payload,
    validate_checker_report,
)
from groundtruth_validation.report import Refusal
from groundtruth_validation.validation_profile import scaffold_checks

REPOSITORY = Path(__file__).resolve().parents[1]


def test_real_scoped_preflight_through_cli() -> None:
    """Run the real metadata checker and label the result as explicitly scoped."""
    result = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY / "tools/preflight.py"),
            "--root",
            str(REPOSITORY),
            "--profile",
            "local-scaffold",
            "--check",
            "metadata",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout
    report = json.loads(result.stdout)
    assert report["gate"] == "preflight_scoped"
    assert report["checks"] == [
        {"name": "metadata", "status": "pass", "returncode": 0, "reason_codes": []}
    ]


@pytest.mark.parametrize(
    "arguments",
    [
        ["--profile", "unknown"],
        ["--check", "CONFIDENTIAL_PAYLOAD"],
        ["--check", "metadata", "--check", "metadata"],
    ],
)
def test_invalid_preflight_selection_is_safe(arguments: list[str]) -> None:
    """Refuse unknown and duplicate selections without executing or echoing them."""
    result = subprocess.run(
        [sys.executable, str(REPOSITORY / "tools/preflight.py"), *arguments],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 4
    assert json.loads(result.stdout)["checks"] == []
    assert "CONFIDENTIAL_PAYLOAD" not in result.stdout + result.stderr


def test_real_failed_checker_preserves_exit_and_codes(repository: Path) -> None:
    """Retain an actual metadata refusal and its authored reason identifiers."""
    (repository / "repository-domain.json").write_text('{"claims":["unearned"]}')
    check = next(item for item in scaffold_checks(REPOSITORY) if item.name == "metadata")
    # Supply the actual existing command and literal receiver root directly.
    check = Check(
        "metadata",
        (
            sys.executable,
            str(REPOSITORY / "tools/check_repository_metadata.py"),
            "--root",
            str(repository),
            "--json",
        ),
        check.location,
        10,
        check.gate,
    )
    outcome, findings = run_check(REPOSITORY, check)
    assert outcome.returncode == 2
    assert outcome.status == "refused"
    assert outcome.reason_codes == ("metadata.shape",)
    assert findings[0].exit_code == 2


def test_native_exit_and_unavailable_module_are_real() -> None:
    """Observe actual native failure and a real absent-module lookup."""
    failed = Check("native-exit", (sys.executable, "-c", "raise SystemExit(7)"), ".", 10)
    outcome, findings = run_check(REPOSITORY, failed)
    assert outcome.returncode == 7
    assert outcome.status == "refused"
    assert findings[0].exit_code == 2
    missing = Check(
        "missing-tool",
        (sys.executable, "--version"),
        ".",
        10,
        module="mpp_required_tool_not_installed",
    )
    outcome, findings = run_check(REPOSITORY, missing)
    assert outcome.returncode is None
    assert findings[0].exit_code == 3


def test_real_nonreport_tool_is_not_a_checker_pass() -> None:
    """Refuse actual plain version output where a strict checker report is required."""
    check = Check("wrong-protocol", (sys.executable, "--version"), ".", 10, "repository_metadata")
    outcome, findings = run_check(REPOSITORY, check)
    assert outcome.returncode == 0
    assert outcome.status == "invalid"
    assert findings[0].code == "check.report"


@pytest.mark.parametrize(
    "fault",
    [
        "gate",
        "scope",
        "status",
        "empty",
        "fields",
        "reason",
        "reason_fields",
        "reason_type",
        "reason_code",
        "exit",
    ],
)
def test_public_checker_protocol_refusals(fault: str) -> None:
    """Reject finite malformed protocol inputs through the public parser API."""
    check = Check(
        "metadata",
        (sys.executable,),
        "tools/check_repository_metadata.py",
        10,
        "repository_metadata",
    )
    data: dict[str, object] = {
        "gate": "repository_metadata",
        "scope": "local_scaffold_infrastructure",
        "status": "refused",
        "reasons": [
            {
                "code": "metadata.shape",
                "path": "repository-domain.json",
                "message": "Authored refusal.",
            }
        ],
    }
    assert validate_checker_report(data, check, 2) == ("metadata.shape",)
    changed = copy.deepcopy(data)
    exit_code = 2
    if fault in ("gate", "scope", "status"):
        changed[fault] = "unexpected"
    elif fault == "empty":
        changed["reasons"] = []
    elif fault == "fields":
        changed["extra"] = "CONFIDENTIAL_PAYLOAD"
    elif fault == "reason":
        changed["reasons"] = ["invalid"]
    elif fault == "reason_fields":
        changed["reasons"] = [{"code": "missing-fields"}]
    elif fault == "reason_type":
        changed["reasons"] = [{"code": 3, "path": ".", "message": "Invalid type"}]
    elif fault == "reason_code":
        changed["reasons"] = [
            {"code": "CONFIDENTIAL_PAYLOAD", "path": ".", "message": "Invalid code"}
        ]
    else:
        exit_code = 7
    with pytest.raises(Refusal) as caught:
        validate_checker_report(changed, check, exit_code)
    assert caught.value.finding.code == "check.protocol"
    assert "CONFIDENTIAL_PAYLOAD" not in caught.value.finding.message


def test_every_actual_outcome_survives_failure_precedence() -> None:
    """Continue after native failure and preserve all actual observed exits."""
    checks = (
        Check("refused", (sys.executable, "-c", "raise SystemExit(7)"), ".", 10),
        Check("unavailable", (str(REPOSITORY / "missing-native-tool"),), ".", 10),
        Check("invalid", ("relative-tool",), ".", 10),
    )
    report = run_checks(REPOSITORY, checks)
    assert report.exit_code == 4
    encoded = json.loads(report.encode())
    assert [item["status"] for item in encoded["checks"]] == ["refused", "unavailable", "invalid"]
    assert [item["returncode"] for item in encoded["checks"]] == [7, None, None]
    assert len(encoded["reasons"]) == 3


def test_full_profile_cannot_be_forged_by_a_subset() -> None:
    """Reject empty, duplicated and falsely complete profile declarations."""
    metadata = next(item for item in scaffold_checks(REPOSITORY) if item.name == "metadata")
    assert run_checks(REPOSITORY, ()).exit_code == 4
    assert run_checks(REPOSITORY, (metadata, metadata)).exit_code == 4
    assert run_checks(REPOSITORY, (metadata,), complete=True).exit_code == 4


def test_full_profile_missing_environment_never_passes(tmp_path: Path) -> None:
    """Attempt every actual required tool path in an unavailable input environment."""
    checks = scaffold_checks(tmp_path)
    result = subprocess.run(
        [sys.executable, str(REPOSITORY / "tools/preflight.py"), "--root", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    report = json.loads(result.stdout)
    assert report["gate"] == "preflight"
    assert result.returncode == 3
    assert len(report["checks"]) == len(checks)
    assert all(
        item["status"] == "unavailable" and item["returncode"] is None for item in report["checks"]
    )


def test_actual_maintained_source_payload_and_real_secret_scanner() -> None:
    """Scan the actual maintained text with the exact installed native producer."""
    payload = source_payload(REPOSITORY)
    assert b"SPIKE-GROUNDTRUTH" in payload
    assert b"GNU AFFERO GENERAL PUBLIC LICENSE" in payload
    scanner = next(item for item in scaffold_checks(REPOSITORY) if item.name == "secret-scan")
    outcome, findings = run_check(REPOSITORY, scanner)
    assert outcome.returncode == 0
    assert findings == []


def test_empty_and_excessive_actual_source_cohorts(tmp_path: Path) -> None:
    """Refuse empty source and finite real files exceeding the total scan budget."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True, timeout=5)
    with pytest.raises(Refusal) as caught:
        source_payload(tmp_path)
    assert caught.value.finding.code == "source.empty"
    for index in range(9):
        (tmp_path / f"input-{index}.txt").write_bytes(b"x" * 1_048_576)
    with pytest.raises(Refusal) as caught:
        source_payload(tmp_path)
    assert caught.value.finding.code == "source.budget"
