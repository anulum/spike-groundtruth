# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — deterministic scoped diagnostics

"""Report authored infrastructure findings without echoing received content."""

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """Identify an authored failure at a repository-relative location.

    Parameters
    ----------
    code : str
        Stable diagnostic identifier.
    path : str
        Authored repository-relative location, never received input text.
    message : str
        Fixed caller-safe diagnostic.
    exit_code : int
        Refused (2), unavailable (3), or invalid configuration (4).
    """

    code: str
    path: str
    message: str
    exit_code: int = 2


class Refusal(Exception):
    """Carry one safe diagnostic across a repository input boundary.

    Parameters
    ----------
    finding : Finding
        Authored failure, without exception or input text.
    returncode : int or None
        Actual reaped tool exit when one was observed at this boundary.
    """

    def __init__(self, finding: Finding, returncode: int | None = None) -> None:
        self.finding = finding
        self.returncode = returncode
        super().__init__(finding.code)


@dataclass
class Report:
    """Aggregate every observed finding for a named infrastructure operation.

    Parameters
    ----------
    gate : str
        Fixed public operation name.
    findings : list[Finding]
        Findings in deterministic execution order.
    """

    gate: str
    findings: list[Finding]

    @property
    def exit_code(self) -> int:
        """Return failure precedence, or zero for this operation's success."""
        return max((item.exit_code for item in self.findings), default=0)

    def encode(self) -> str:
        """Return stable JSON for the named infrastructure scope.

        Returns
        -------
        str
            One newline-terminated JSON object with no observation clock.
        """
        status = {0: "pass", 2: "refused", 3: "unavailable", 4: "invalid"}[self.exit_code]
        return (
            json.dumps(
                {
                    "gate": self.gate,
                    "scope": "local_scaffold_infrastructure",
                    "status": status,
                    "reasons": [
                        {"code": item.code, "path": item.path, "message": item.message}
                        for item in self.findings
                    ],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
            + "\n"
        )
