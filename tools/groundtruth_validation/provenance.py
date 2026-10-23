# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — native source and licence provenance

"""Verify maintained source notices, exact JSON sidecars and licensed assets."""

import hashlib
from pathlib import Path

from groundtruth_validation.inputs import read_file, read_json
from groundtruth_validation.report import Finding, Refusal, Report
from groundtruth_validation.structure import maintained_paths

NOTICE_LINES = (
    "SPDX-License-" + "Identifier: AGPL-3.0-or-later",
    "Commercial license available",
    "© Concepts 1996–2026 Miroslav Šotek. All rights reserved.",
    "© Code 2020–2026 Miroslav Šotek. All rights reserved.",
    "ORCID: 0009-0009-3560-0851",
    "Contact: www.anulum.li | protoscience@anulum.li",
)
COPYRIGHT_LINES = (
    "SPDX-FileCopyrightText: 1996-2026 Miroslav Šotek <protoscience@anulum.li> (concepts)",
    "SPDX-FileCopyrightText: 2020-2026 Miroslav Šotek <protoscience@anulum.li> (code)",
)
ASSET_SHA256 = {
    "docs/assets/anulum_logo_company.jpg": "d98a731a2b4b3b8880979d2e2f2c5cb722cc45d3f75b988e81c301902c7d1143",
    "docs/assets/anulum_logo.png": "fe4b3b24226e87045d4aac09284f30ee8a83bd95f9af0509272a063e284067d3",
    "docs/assets/fortis_studio_logo.jpg": "844c5d764c8ad0a030e8f7b83c7e878bb4ebec42ea6e40223f65f344769568c0",
}
LICENCE_SHA256 = "d8a6cc31abc16b6748c7a21f21611f5a1ec33f67d22ca23d7da1c19b95496bee"


def validate_notice(text: str, *, markdown: bool = False, sidecar: bool = False) -> bool:
    """Check the exact native notice shape and project ownership line.

    Parameters
    ----------
    text : str
        Decoded source bytes.
    markdown : bool
        Require an invisible HTML comment around the seven records.
    sidecar : bool
        Require unprefixed records and exact additional copyright records.

    Returns
    -------
    bool
        Whether the source has the complete applicable native notice.
    """
    lines = text.splitlines()
    if markdown:
        if not lines or lines[0] != "<!--" or len(lines) < 9 or lines[8] != "-->":
            return False
        records = lines[1:8]
    elif sidecar:
        if len(lines) != 9 or tuple(lines[7:]) != COPYRIGHT_LINES:
            return False
        records = lines[:7]
    else:
        if any(not line.startswith("# ") for line in lines[:7]):
            return False
        records = [line.removeprefix("# ") for line in lines[:7]]
    return (
        len(records) == 7
        and tuple(records[:6]) == NOTICE_LINES
        and records[6].startswith("SPIKE-GROUNDTRUTH — ")
        and len(records[6]) > len("SPIKE-GROUNDTRUTH — ")
    )


def validate_provenance(root: Path) -> Report:
    """Validate every actual maintained file's ownership or exact licensed bytes.

    Parameters
    ----------
    root : Path
        Standalone repository with a real Git-maintained source inventory.

    Returns
    -------
    Report
        Located provenance findings; absence and unreadability never pass.
    """
    report = Report("source_provenance", [])
    try:
        paths = maintained_paths(root)
    except Refusal as exc:
        report.findings.append(exc.finding)
        return report
    if not paths:
        report.findings.append(Finding("source.empty", ".", "No maintained source is available."))
    for relative in paths:
        try:
            if relative in ASSET_SHA256:
                raw = read_file(root, relative, limit=2_097_152)
                if hashlib.sha256(raw).hexdigest() != ASSET_SHA256[relative]:
                    report.findings.append(
                        Finding(
                            "asset.identity",
                            relative,
                            "Branding asset differs from licensed source.",
                        )
                    )
                continue
            if relative in ("LICENSE", "LICENSES/AGPL-3.0-or-later.txt"):
                if hashlib.sha256(read_file(root, relative)).hexdigest() != LICENCE_SHA256:
                    report.findings.append(
                        Finding(
                            "licence.identity",
                            relative,
                            "Standard licence text differs from the preserved original.",
                        )
                    )
                continue
            if relative.endswith(".json"):
                read_json(root, relative)
                sidecar = relative + ".license"
                if not validate_notice(read_file(root, sidecar).decode("utf-8"), sidecar=True):
                    report.findings.append(
                        Finding(
                            "json.sidecar",
                            relative,
                            "JSON needs its exact regular ownership sidecar.",
                        )
                    )
                continue
            text = read_file(root, relative).decode("utf-8", errors="strict")
            if not validate_notice(
                text, markdown=relative.endswith(".md"), sidecar=relative.endswith(".license")
            ):
                report.findings.append(
                    Finding(
                        "source.notice",
                        relative,
                        "Source notice is missing, conflicting or incorrect.",
                    )
                )
        except Refusal as exc:
            report.findings.append(exc.finding)
        except UnicodeError:
            report.findings.append(
                Finding("source.encoding", relative, "Unrecognised binary or invalid UTF-8 source.")
            )
    return report
