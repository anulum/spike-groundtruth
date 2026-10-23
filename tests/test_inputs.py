# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — strict file and JSON boundary tests

"""Exercise the public finite-input API using actual filesystem inputs."""

from pathlib import Path

import pytest

from groundtruth_validation.inputs import parse_json, read_file, read_json
from groundtruth_validation.report import Refusal


@pytest.mark.parametrize("relative", ["../outside", "/absolute", ""])
def test_invalid_configured_paths(tmp_path: Path, relative: str) -> None:
    """Reject configured paths outside the repository-relative namespace."""
    with pytest.raises(Refusal) as caught:
        read_file(tmp_path, relative)
    assert caught.value.finding.code == "path.invalid"
    assert caught.value.finding.path == "."


def test_missing_root_and_linked_root(tmp_path: Path) -> None:
    """Refuse nonexistent roots and explicit linked repository roots."""
    for root in (tmp_path / "missing", tmp_path / "linked"):
        if root.name == "linked":
            root.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(Refusal) as caught:
            read_file(root, "input.json")
        assert caught.value.finding.code == "root.invalid"


def test_nonregular_missing_and_linked_input(tmp_path: Path) -> None:
    """Refuse unavailable, directory and symlink inputs without reading targets."""
    target = tmp_path / "input.json"
    with pytest.raises(Refusal) as caught:
        read_file(tmp_path, target.name)
    assert caught.value.finding.code == "file.unavailable"
    target.mkdir()
    with pytest.raises(Refusal) as caught:
        read_file(tmp_path, target.name)
    assert caught.value.finding.code == "file.kind"
    link = tmp_path / "linked.json"
    link.symlink_to(target)
    with pytest.raises(Refusal) as caught:
        read_file(tmp_path, link.name)
    assert caught.value.finding.code == "file.link"


def test_size_boundary_reads_only_finite_bytes(tmp_path: Path) -> None:
    """Accept the documented limit and refuse a file one byte larger."""
    target = tmp_path / "input"
    content = b"x" * 1_048_576
    target.write_bytes(content)
    assert read_file(tmp_path, "input") == content
    target.write_bytes(content + b"x")
    with pytest.raises(Refusal) as caught:
        read_file(tmp_path, "input")
    assert caught.value.finding.code == "file.size"


@pytest.mark.parametrize("limit", [0, -1, 8_388_609])
def test_invalid_file_limits(tmp_path: Path, limit: int) -> None:
    """Reject configurations which could remove the finite file-read bound."""
    with pytest.raises(Refusal) as caught:
        read_file(tmp_path, "input", limit=limit)
    assert caught.value.finding.code == "limit.invalid"


def test_tool_json_buffer_has_the_same_finite_bound() -> None:
    """Reject an actual oversized tool-report buffer before parsing its contents."""
    with pytest.raises(Refusal) as caught:
        parse_json(b"x" * 1_048_577, "tools/preflight.py")
    assert caught.value.finding.code == "json.size"


@pytest.mark.parametrize(
    "content",
    [
        b'{"key":1,"key":2}',
        b'{"nested":{"key":1,"key":2}}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b'{"x":1e9999}',
        b'{"x":"\\ud800"}',
        b'{"\\udfff":1}',
        b'{"x":"\xff"}',
        b'{"x":',
        b'{"x":' + b"[" * 2000 + b"]" * 2000 + b"}",
    ],
)
def test_ambiguous_or_invalid_json(tmp_path: Path, content: bytes) -> None:
    """Reject duplicates, nonfinite numbers, malformed text and excessive nesting."""
    (tmp_path / "input.json").write_bytes(content)
    with pytest.raises(Refusal) as caught:
        read_json(tmp_path, "input.json")
    assert caught.value.finding.code == "json.invalid"
    assert caught.value.finding.message == "Input is not strict UTF-8 JSON."


@pytest.mark.parametrize("content", [b"null", b"[]", b'"text"', b"1", b"true"])
def test_object_required(tmp_path: Path, content: bytes) -> None:
    """Refuse JSON scalar and list roots through the public file parser."""
    (tmp_path / "input.json").write_bytes(content)
    with pytest.raises(Refusal) as caught:
        read_json(tmp_path, "input.json")
    assert caught.value.finding.code == "json.object"


def test_unicode_and_nested_finite_values(tmp_path: Path) -> None:
    """Retain source bytes while accepting valid nested UTF-8 JSON values."""
    raw = '{"label":"Šotek 🧠","values":[1,1.25,null,false,{},[]]}\n'.encode()
    (tmp_path / "input.json").write_bytes(raw)
    parsed, source = read_json(tmp_path, "input.json")
    assert source == raw
    assert parsed == {"label": "Šotek 🧠", "values": [1, 1.25, None, False, {}, []]}
