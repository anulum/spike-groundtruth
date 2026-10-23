# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — complete hash-lock parsing

"""Parse exact direct requirements and complete hash-locked package entries."""

import re

from groundtruth_validation.report import Finding, Refusal


def parse_lock(content: bytes) -> dict[str, tuple[str, frozenset[str]]]:
    """Parse a complete finite lock with exact versions and SHA-256 artifacts.

    Parameters
    ----------
    content : bytes
        UTF-8 lock contents already read within the finite file boundary.

    Returns
    -------
    dict[str, tuple[str, frozenset[str]]]
        Canonical package names, exact versions and nonempty allowed hashes.

    Raises
    ------
    Refusal
        An entry is unpinned, unhashed, duplicated or not a supported lock line.
    ImportError
        The required locked packaging implementation is unavailable.
    """
    from packaging.utils import canonicalize_name
    from packaging.version import InvalidVersion, Version

    result: dict[str, tuple[str, frozenset[str]]] = {}
    try:
        text = re.sub(r"\\\r?\n", " ", content.decode("utf-8", errors="strict"))
        for line in text.splitlines():
            literal = line.split("#", 1)[0].strip()
            if not literal:
                continue
            match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s;]+)\s+(.+)", literal)
            if match is None:
                raise ValueError("entry")
            name = canonicalize_name(match[1])
            version = match[2]
            Version(version)
            tokens = match[3].split()
            if name in result or any(
                not re.fullmatch(r"--hash=sha256:[0-9a-f]{64}", token) for token in tokens
            ):
                raise ValueError("hash")
            result[name] = (
                version,
                frozenset(token.removeprefix("--hash=sha256:") for token in tokens),
            )
        if not result:
            raise ValueError("empty")
    except (ValueError, UnicodeError, InvalidVersion) as exc:
        raise Refusal(
            Finding(
                "dependency.lock",
                "requirements-dev.txt",
                "Every unique lock entry needs an exact valid version and SHA-256 artifacts.",
                4,
            )
        ) from exc
    return result


def parse_direct(content: bytes) -> dict[str, str]:
    """Parse justified exact direct development requirements without hidden sources.

    Parameters
    ----------
    content : bytes
        UTF-8 direct requirements with authored comment lines.

    Returns
    -------
    dict[str, str]
        Unique canonical direct tool names and exact versions.

    Raises
    ------
    Refusal
        Requirements are missing, duplicated, mutable or select a foreign source.
    ImportError
        The locked packaging parser is unavailable.
    """
    from packaging.requirements import InvalidRequirement, Requirement
    from packaging.utils import canonicalize_name

    result: dict[str, str] = {}
    try:
        for line in content.decode("utf-8", errors="strict").splitlines():
            literal = line.split("#", 1)[0].strip()
            if not literal:
                continue
            requirement = Requirement(literal)
            name = canonicalize_name(requirement.name)
            pins = list(requirement.specifier)
            if (
                name in result
                or requirement.url
                or requirement.extras
                or requirement.marker
                or len(pins) != 1
                or pins[0].operator != "=="
                or "*" in pins[0].version
            ):
                raise ValueError("pin")
            result[name] = pins[0].version
        if not result:
            raise ValueError("empty")
    except (ValueError, UnicodeError, InvalidRequirement) as exc:
        raise Refusal(
            Finding(
                "dependency.direct",
                "requirements-dev.in",
                "Direct tools need unique exact versions without alternate sources or implicit lanes.",
                4,
            )
        ) from exc
    return result
