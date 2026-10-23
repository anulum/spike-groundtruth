# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — preflight invocation and scope

"""Expose fixed profile selection without artifact-controlled commands or skips."""

from collections.abc import Sequence
from pathlib import Path

from groundtruth_validation.cli import Parser, emit_report
from groundtruth_validation.preflight import PreflightReport, run_checks
from groundtruth_validation.report import Finding, Refusal
from groundtruth_validation.validation_profile import scaffold_checks


def preflight_main(argv: Sequence[str] | None = None) -> int:
    """Run actual required checks or an explicitly limited named operation.

    Parameters
    ----------
    argv : Sequence[str] or None
        Literal arguments or the native process command line.

    Returns
    -------
    int
        Scoped preflight result with every attempted outcome and actual exit.
        A named subset reports preflight_scoped, never full profile acceptance.
    """
    parser = Parser(description="Execute actual SPIKE-GROUNDTRUTH infrastructure checks.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--profile", choices=("local-scaffold",), default="local-scaffold")
    parser.add_argument(
        "--check",
        action="append",
        help="Run only a named scoped check; repeat for an explicit subset.",
    )
    parser.add_argument("--json", action="store_true")
    try:
        options = parser.parse_args(argv)
        checks = scaffold_checks(options.root)
        selection = options.check
        if selection is not None:
            by_name = {item.name: item for item in checks}
            if len(set(selection)) != len(selection) or any(
                name not in by_name for name in selection
            ):
                raise Refusal(
                    Finding(
                        "preflight.selection",
                        ".",
                        "Scoped check names must be known and unique.",
                        4,
                    )
                )
            checks = tuple(by_name[name] for name in selection)
        report = run_checks(options.root, checks, complete=selection is None)
    except Refusal as exc:
        report = PreflightReport("preflight", [exc.finding])
    return emit_report(report)
