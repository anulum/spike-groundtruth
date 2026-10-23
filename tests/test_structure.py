# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — maintained source structure boundary tests

"""Inspect real Git and filesystem failures through the public structure API."""

import os
import subprocess
from pathlib import Path

import pytest

from groundtruth_validation.report import Refusal
from groundtruth_validation.structure import maintained_paths, validate_structure


def init_repository(root: Path) -> None:
    """Initialize a real bounded standalone test repository.

    Parameters
    ----------
    root : Path
        Directory that will own its actual Git metadata.
    """
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True, timeout=5)


def test_no_parent_repository_discovery(tmp_path: Path) -> None:
    """Do not mistake the containing repository's source for the requested root."""
    with pytest.raises(Refusal) as caught:
        maintained_paths(tmp_path)
    assert caught.value.finding.code == "git.root"


def test_invalid_real_git_metadata(tmp_path: Path) -> None:
    """Distinguish an existing directory from an actual usable Git repository."""
    (tmp_path / ".git").mkdir()
    with pytest.raises(Refusal) as caught:
        maintained_paths(tmp_path)
    assert caught.value.finding.code == "git.repository"


def test_absent_git_tool_is_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the public inventory API in a real environment with no Git executable."""
    init_repository(tmp_path)
    monkeypatch.setenv("PATH", "")
    with pytest.raises(Refusal) as caught:
        maintained_paths(tmp_path)
    assert caught.value.finding.code == "git.unavailable"


def test_non_utf8_source_name_is_refused(tmp_path: Path) -> None:
    """Refuse an actual non-UTF-8 filename rather than echoing undecodable bytes."""
    init_repository(tmp_path)
    descriptor = os.open(os.fsencode(tmp_path) + b"/invalid-\xff", os.O_CREAT | os.O_WRONLY, 0o600)
    os.close(descriptor)
    with pytest.raises(Refusal) as caught:
        maintained_paths(tmp_path)
    assert caught.value.finding.code == "path.encoding"


def test_source_tree_and_private_ignore_policy(tmp_path: Path) -> None:
    """Retain complete missing-path, private-source and generated-source failures."""
    init_repository(tmp_path)
    private = tmp_path / "docs/internal/note.md"
    private.parent.mkdir(parents=True)
    private.write_text("finite private-path rejection input\n")
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "-f", "--", "docs/internal/note.md"],
        check=True,
        timeout=5,
    )
    (tmp_path / "unexpected.whl").write_bytes(b"finite unsupported binary input")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / ".gitignore").write_text(
        "docs/internal/\ndocs/internal/**\n!docs/internal/note.md\n"
    )
    report = validate_structure(tmp_path)
    codes = {item.code for item in report.findings}
    assert codes >= {
        "file.unavailable",
        "directory.required",
        "tree.forbidden",
        "private.source",
        "generated.source",
        "private.ignore",
    }
    (tmp_path / ".gitignore").write_bytes(b"\xff")
    assert "ignore.encoding" in {item.code for item in validate_structure(tmp_path).findings}


def test_required_regular_directory_and_valid_ignore(tmp_path: Path) -> None:
    """Accept actual required directories and preserve the private ignore invariant."""
    init_repository(tmp_path)
    (tmp_path / "LICENSES").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".gitignore").write_text("docs/internal/\ndocs/internal/**\n")
    report = validate_structure(tmp_path)
    assert "directory.required" not in {item.code for item in report.findings}
    assert "private.ignore" not in {item.code for item in report.findings}
