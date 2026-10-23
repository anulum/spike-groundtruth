# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — actual native payload and bootstrap provenance tests

"""Verify actual installed native bytes and reject finite source and payload faults."""

from pathlib import Path

from groundtruth_validation.native_tools import verify_native_tools

REPOSITORY = Path(__file__).resolve().parents[1]


def test_actual_native_release_payloads() -> None:
    """Bind both actual executables to their primary release and bootstrap source."""
    assert verify_native_tools(REPOSITORY) == []


def test_native_provenance_and_recipe_refusals(tmp_path: Path) -> None:
    """Refuse missing, weakened and undecodable source configuration."""
    assert verify_native_tools(tmp_path)[0].exit_code == 3
    (tmp_path / "native-tool-provenance.json").write_text("{}")
    assert verify_native_tools(tmp_path)[0].code == "native.provenance"
    (tmp_path / "native-tool-provenance.json").write_bytes(
        (REPOSITORY / "native-tool-provenance.json").read_bytes()
    )
    (tmp_path / "Makefile").write_bytes(b"\xff")
    assert verify_native_tools(tmp_path)[0].code == "native.recipe"


def test_unavailable_changed_and_linked_native_payloads(tmp_path: Path) -> None:
    """Inspect real file faults without executing a substituted native producer."""
    (tmp_path / "native-tool-provenance.json").write_bytes(
        (REPOSITORY / "native-tool-provenance.json").read_bytes()
    )
    (tmp_path / "Makefile").write_text("metadata:\n\ttrue\n")
    assert {item.code for item in verify_native_tools(tmp_path)} == {"native.unavailable"}
    tool = tmp_path / ".tool-cache/native/actionlint/actionlint"
    tool.parent.mkdir(parents=True)
    tool.write_bytes(b"finite invalid payload input, never executed")
    assert {item.code for item in verify_native_tools(tmp_path)} >= {
        "native.identity",
        "native.bootstrap",
    }
    tool.unlink()
    tool.symlink_to(REPOSITORY / ".tool-cache/native/actionlint/actionlint")
    assert "native.file" in {item.code for item in verify_native_tools(tmp_path)}
