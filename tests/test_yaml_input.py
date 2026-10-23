# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — finite YAML configuration input tests

"""Exercise actual duplicate-free YAML parsing and missing parser environments."""

import json
from pathlib import Path

import pytest

from groundtruth_validation.report import Refusal
from groundtruth_validation.yaml_input import read_yaml
from tests.native_process import run_isolated


def test_literal_keys_and_scalars(tmp_path: Path) -> None:
    """Keep workflow on keys and Boolean-looking scalars as their literal text."""
    (tmp_path / "input.yml").write_text(
        "on:\n  pull_request:\nenabled: true\nitems: [1, false, null]\n"
    )
    assert read_yaml(tmp_path, "input.yml") == {
        "on": {"pull_request": ""},
        "enabled": "true",
        "items": ["1", "false", "null"],
    }


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"key: 1\nkey: 2\n",
        b"? [key, value]\n: 1\n",
        b"key: &x [1]\nother: *x\n",
        b"key: [",
        b'key: "\\ud800"',
        b"key: \xff",
        b"key: 1\n---\nkey: 2",
    ],
)
def test_invalid_ambiguous_or_aliased_yaml(tmp_path: Path, raw: bytes) -> None:
    """Refuse malformed text, duplicates, complex keys, aliases and multiple documents."""
    (tmp_path / "input.yml").write_bytes(raw)
    with pytest.raises(Refusal) as caught:
        read_yaml(tmp_path, "input.yml")
    assert caught.value.finding.code == "yaml.invalid"


def test_mapping_required(tmp_path: Path) -> None:
    """Reject a real YAML sequence where configuration requires a mapping."""
    (tmp_path / "input.yml").write_text("[1, 2]")
    with pytest.raises(Refusal) as caught:
        read_yaml(tmp_path, "input.yml")
    assert caught.value.finding.code == "yaml.mapping"


def test_missing_file_remains_unavailable(tmp_path: Path) -> None:
    """Preserve a file boundary's unavailable status through the YAML API."""
    with pytest.raises(Refusal) as caught:
        read_yaml(tmp_path, "missing.yml")
    assert caught.value.finding.exit_code == 3


def test_real_interpreter_without_yaml(workflow_repository: Path) -> None:
    """Require the locked YAML parser when the actual isolated interpreter lacks it."""
    command = Path(__file__).resolve().parents[1] / "tools/check_workflow_policy.py"
    result = run_isolated(command, "--root", str(workflow_repository), "--json")
    assert result.returncode == 3
    assert {row["code"] for row in json.loads(result.stdout)["reasons"]} == {"yaml.tool"}
    assert result.stderr == ""
