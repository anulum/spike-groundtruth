# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — actual maintained source provenance tests

"""Exercise native notices, exact sidecars and preservation of licensed bytes."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from groundtruth_validation.provenance import validate_notice, validate_provenance

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture
def source_repository(tmp_path: Path) -> Path:
    """Create a real independent Git repository for finite provenance inputs.

    Parameters
    ----------
    tmp_path : Path
        Per-test directory on the Samsung working filesystem.

    Returns
    -------
    Path
        Actual Git repository, with no emulated command producer.
    """
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True, timeout=5)
    return tmp_path


def test_actual_maintained_source_through_cli() -> None:
    """Accept the repository's real native notices and licensed source assets."""
    result = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY / "tools/check_source_provenance.py"),
            "--root",
            str(REPOSITORY),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["gate"] == "source_provenance"


def test_missing_repository_and_empty_source(tmp_path: Path, source_repository: Path) -> None:
    """Keep unavailable Git and empty maintained source as explicit failures."""
    assert validate_provenance(tmp_path / "missing").exit_code == 3
    report = validate_provenance(source_repository)
    assert report.exit_code == 2
    assert report.findings[0].code == "source.empty"


def test_json_needs_its_exact_regular_sidecar(source_repository: Path) -> None:
    """Refuse missing and malformed sidecars, and accept the actual notice bytes."""
    root = source_repository
    (root / "input.json").write_text('{"finite":true}')
    assert validate_provenance(root).findings[0].code == "file.unavailable"
    sidecar = root / "input.json.license"
    sidecar.write_text("incorrect ownership\n")
    assert "json.sidecar" in {item.code for item in validate_provenance(root).findings}
    sidecar.write_bytes((REPOSITORY / "repository-domain.json.license").read_bytes())
    assert validate_provenance(root).exit_code == 0


def test_conflicting_notice_and_invalid_source_encoding(source_repository: Path) -> None:
    """Refuse conflicting SPDX records and unrecognised binary source."""
    source = (REPOSITORY / "tools/groundtruth_validation/report.py").read_bytes()
    (source_repository / "changed.py").write_bytes(source.replace(b"AGPL-3.0-or-later", b"MIT", 1))
    (source_repository / "binary.dat").write_bytes(b"\xff\xfe")
    report = validate_provenance(source_repository)
    assert {item.code for item in report.findings} == {"source.notice", "source.encoding"}


def test_licence_and_asset_mutation_are_refused(source_repository: Path) -> None:
    """Check licensed raw identities rather than trusting a filename or notice."""
    (source_repository / "LICENSE").write_text("replaced licence")
    target = source_repository / "docs/assets/anulum_logo.png"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"replaced image")
    assert {item.code for item in validate_provenance(source_repository).findings} == {
        "licence.identity",
        "asset.identity",
    }


@pytest.mark.parametrize(
    "text",
    ["", "<!--\nvisible", "# SPDX-License-" + "Identifier: MIT\n", "<!--\n" + "text\n" * 8],
)
def test_markdown_notice_requires_invisible_exact_records(text: str) -> None:
    """Reject absent, visible, short and incorrectly terminated Markdown notices."""
    assert not validate_notice(text, markdown=True)


def test_project_purpose_line_is_required() -> None:
    """Reject a notice belonging to another project or missing a module purpose."""
    original = (REPOSITORY / "tools/groundtruth_validation/report.py").read_text()
    assert validate_notice(original)
    assert not validate_notice(original.replace("# ", "", 7))
    assert not validate_notice(original.replace("SPIKE-GROUNDTRUTH —", "OTHER —"))
    assert not validate_notice("\n".join(original.splitlines()[:6]))
    assert not validate_notice("\n".join(original.splitlines()[:6]) + "\n# SPIKE-GROUNDTRUTH — ")


def test_invalid_invocation_stays_structured() -> None:
    """Keep common checker argument errors parseable without received text."""
    result = subprocess.run(
        [sys.executable, str(REPOSITORY / "tools/check_source_provenance.py"), "--bad"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 4
    assert json.loads(result.stdout)["reasons"][0]["code"] == "cli.invalid"


@pytest.mark.parametrize("mutation", ["missing_contact", "noncanonical_dates", "duplicate_owner"])
def test_json_owner_records_match_canonical_commit_policy(
    source_repository: Path, mutation: str
) -> None:
    """Refuse real sidecars with obsolete or ambiguous owner records."""
    (source_repository / "input.json").write_text('{"finite":true}')
    sidecar = (REPOSITORY / "repository-domain.json.license").read_text()
    if mutation == "missing_contact":
        sidecar = sidecar.replace(" <protoscience@anulum.li>", "")
    elif mutation == "noncanonical_dates":
        sidecar = sidecar.replace(
            "SPDX-FileCopyrightText: 1996-2026", "SPDX-FileCopyrightText: 1996–2026"
        )
    else:
        sidecar += (
            "SPDX-FileCopyrightText: 2020-2026 Miroslav Šotek <protoscience@anulum.li> (code)\n"
        )
    (source_repository / "input.json.license").write_text(sidecar)
    assert "json.sidecar" in {item.code for item in validate_provenance(source_repository).findings}
