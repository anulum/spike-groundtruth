# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — structured diagnostic contract tests

"""Verify the public report protocol and multiple-failure precedence."""

import json

import pytest

from groundtruth_validation.report import Finding, Report


@pytest.mark.parametrize(("codes", "expected"), [([], 0), ([2], 2), ([2, 3], 3), ([3, 2, 4], 4)])
def test_exit_precedence_preserves_all_findings(codes: list[int], expected: int) -> None:
    """Retain all observed reasons even when a higher-precedence failure exists."""
    report = Report("repository_metadata", [Finding("authored", ".", "Fixed.", x) for x in codes])
    assert report.exit_code == expected
    encoded = report.encode()
    assert encoded.endswith("\n")
    assert len(json.loads(encoded)["reasons"]) == len(codes)
    assert (
        json.loads(encoded)["status"]
        == {0: "pass", 2: "refused", 3: "unavailable", 4: "invalid"}[expected]
    )
