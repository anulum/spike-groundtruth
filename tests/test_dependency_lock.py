# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — exact direct and complete hash-lock input tests

"""Exercise actual locked input bytes and finite malformed requirement inputs."""

from pathlib import Path

import pytest

from groundtruth_validation.dependency_lock import parse_direct, parse_lock
from groundtruth_validation.report import Refusal

REPOSITORY = Path(__file__).resolve().parents[1]


def test_complete_actual_lock_and_direct_inputs() -> None:
    """Reconcile every actual direct tool with the real complete hashed lock."""
    lock = parse_lock((REPOSITORY / "requirements-dev.txt").read_bytes())
    direct = parse_direct((REPOSITORY / "requirements-dev.in").read_bytes())
    assert set(direct).issubset(lock)
    assert all(lock[name][0] == version for name, version in direct.items())
    assert all(hashes for _, hashes in lock.values())
    assert direct["mypy"] == "1.20.2"


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"package>=1.0",
        b"package==1.0",
        b"package==bad --hash=sha256:" + b"0" * 64,
        b"package==1.0 --hash=md5:" + b"0" * 32,
        b"--index-url https://example.invalid",
        b"package==1.0 --hash=sha256:" + b"0" * 64 + b"\npackage==1.0 --hash=sha256:" + b"0" * 64,
        b"package==1.0; python_version>'3' --hash=sha256:" + b"0" * 64,
        b"\xff",
    ],
)
def test_lock_refuses_mutable_unhashed_duplicate_and_invalid_entries(content: bytes) -> None:
    """Reject actual syntax and policy faults instead of accepting a partial lock."""
    with pytest.raises(Refusal) as caught:
        parse_lock(content)
    assert caught.value.finding.code == "dependency.lock"
    assert caught.value.finding.exit_code == 4


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"package",
        b"package>=1.0",
        b"package==1.*",
        b"package[extra]==1.0",
        b"package==1.0; python_version>'3'",
        b"package @ https://example.invalid/package.whl",
        b"package==1.0\npackage==1.0",
        b"!!!",
        b"\xff",
    ],
)
def test_direct_requirements_refuse_hidden_or_mutable_sources(content: bytes) -> None:
    """Keep exact direct tools separate from alternate sources and implicit lanes."""
    with pytest.raises(Refusal) as caught:
        parse_direct(content)
    assert caught.value.finding.code == "dependency.direct"
    assert caught.value.finding.exit_code == 4
