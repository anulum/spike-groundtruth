# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — bounded regular-file and strict JSON input

"""Read finite repository-owned files without following symbolic links."""

import json
import math
import stat
from pathlib import Path

from groundtruth_validation.report import Finding, Refusal

MAX_BYTES = 1_048_576


def read_file(root: Path, relative: str, *, limit: int = MAX_BYTES) -> bytes:
    """Read a bounded regular file below a regular repository root.

    Parameters
    ----------
    root : Path
        Explicit repository directory.
    relative : str
        Authored relative file path.
    limit : int
        Finite byte limit, at most eight MiB; one MiB by default.

    Returns
    -------
    bytes
        At most the configured finite limit of file content.

    Raises
    ------
    Refusal
        The path is unavailable, nonregular, linked, or too large.
    """
    location = Path(relative)
    if not 0 < limit <= 8 * MAX_BYTES:
        raise Refusal(Finding("limit.invalid", ".", "Invalid configured file limit.", 4))
    if location.is_absolute() or ".." in location.parts or not location.parts:
        raise Refusal(Finding("path.invalid", ".", "Invalid configured input path.", 4))
    try:
        if root.is_symlink() or not root.is_dir():
            raise Refusal(Finding("root.invalid", ".", "Repository root is not a directory.", 4))
        candidate = root
        for part in location.parts:
            candidate /= part
            if candidate.is_symlink():
                raise Refusal(Finding("file.link", relative, "Linked input is not accepted."))
        mode = candidate.stat().st_mode
        if not stat.S_ISREG(mode):
            raise Refusal(Finding("file.kind", relative, "Input must be a regular file."))
        with candidate.open("rb") as stream:
            content = stream.read(limit + 1)
    except OSError as exc:
        raise Refusal(
            Finding("file.unavailable", relative, "Required file is unavailable.", 3)
        ) from exc
    if len(content) > limit:
        raise Refusal(Finding("file.size", relative, "Input exceeds the configured byte limit."))
    return content


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject ambiguous object keys before exposing a parsed JSON object."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate")
        result[key] = value
    return result


def _constant(_value: str) -> object:
    """Refuse nonstandard numeric JSON constants."""
    raise ValueError("constant")


def _unicode_and_numbers(value: object) -> None:
    """Check escaped Unicode and floats after strict lexical parsing."""
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("nonfinite")
    elif isinstance(value, dict):
        for key, item in value.items():
            _unicode_and_numbers(key)
            _unicode_and_numbers(item)
    elif isinstance(value, list):
        for item in value:
            _unicode_and_numbers(item)


def read_json(root: Path, relative: str) -> tuple[dict[str, object], bytes]:
    """Read an unambiguous UTF-8 JSON object and retain its exact source bytes.

    Parameters
    ----------
    root : Path
        Explicit repository directory.
    relative : str
        Authored relative input path.

    Returns
    -------
    tuple[dict[str, object], bytes]
        Parsed object and original bytes, never reserialized for a digest.

    Raises
    ------
    Refusal
        Input is unavailable, malformed, ambiguous, or not a JSON object.
    """
    content = read_file(root, relative)
    return parse_json(content, relative), content


def parse_json(content: bytes, relative: str) -> dict[str, object]:
    """Parse a finite strict JSON object from a file or actual tool output.

    Parameters
    ----------
    content : bytes
        At most one MiB of actual UTF-8 input bytes.
    relative : str
        Authored safe repository-relative diagnostic location.

    Returns
    -------
    dict[str, object]
        Unambiguous JSON object, without input normalisation or code selection.

    Raises
    ------
    Refusal
        Bytes exceed the limit or violate the strict object-input contract.
    """
    if len(content) > MAX_BYTES:
        raise Refusal(Finding("json.size", relative, "JSON input exceeds the finite byte limit."))
    try:
        parsed: object = json.loads(
            content.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs,
            parse_constant=_constant,
        )
        _unicode_and_numbers(parsed)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Refusal(Finding("json.invalid", relative, "Input is not strict UTF-8 JSON.")) from exc
    if not isinstance(parsed, dict):
        raise Refusal(Finding("json.object", relative, "Input must be a JSON object."))
    return {str(key): value for key, value in parsed.items()}
