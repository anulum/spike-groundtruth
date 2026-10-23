# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — complete maintained repository structure

"""Inspect actual required paths and Git-maintained source boundaries."""

import shutil
from pathlib import Path

from groundtruth_validation.execution import run_tool
from groundtruth_validation.inputs import read_file
from groundtruth_validation.paths import REQUIRED_DIRECTORIES, REQUIRED_PATHS
from groundtruth_validation.report import Finding, Refusal, Report

FORBIDDEN_ROOTS = (
    ".env",
    "AGENTS.md",
    "BACKUP",
    "ARCHIVE",
    "CLAUDE.md",
    "CODEX.md",
    "GEMINI.md",
    "GROK.md",
    "KIMI.md",
    "agentic_group_workspace",
    ".agents",
    ".claude",
    ".codex",
    ".coordination",
    ".synapse",
    "agentic-shared",
    "04_ARCANE_SAPIENCE",
    "node_modules",
    "src",
)


def maintained_paths(root: Path) -> list[str]:
    """Read actual tracked and nonignored untracked source paths from Git.

    Parameters
    ----------
    root : Path
        Explicit repository root.

    Returns
    -------
    list[str]
        Sorted unique UTF-8 repository-relative source paths.

    Raises
    ------
    Refusal
        Git is unavailable, input is not a repository, or names are invalid.
    """
    git_directory = root / ".git"
    if git_directory.is_symlink() or not git_directory.is_dir():
        raise Refusal(Finding("git.root", ".git", "Root must own its standalone Git directory.", 3))
    try:
        child = run_tool(
            [
                shutil.which("git") or "/unavailable-required-git",
                "-C",
                str(root),
                "--git-dir=.git",
                "--work-tree=.",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            root=root,
            timeout=5,
        )
    except Refusal as exc:
        raise Refusal(
            Finding("git.unavailable", ".git", "Required Git inventory is unavailable.", 3)
        ) from exc
    if child.returncode:
        raise Refusal(Finding("git.repository", ".git", "Git repository inventory failed.", 3))
    try:
        paths = sorted(set(child.stdout.decode("utf-8", errors="strict").split("\0")) - {""})
    except UnicodeError as exc:
        raise Refusal(Finding("path.encoding", ".", "Source path names must be UTF-8.")) from exc
    return paths


def validate_structure(root: Path) -> Report:
    """Check the complete initial path policy and private-source exclusion.

    Parameters
    ----------
    root : Path
        Repository whose real filesystem and Git cohort are inspected.

    Returns
    -------
    Report
        Complete path findings, without claiming file semantic acceptance.
    """
    report = Report("repository_structure", [])
    for relative in REQUIRED_PATHS:
        try:
            if relative in REQUIRED_DIRECTORIES:
                path = root / relative
                if path.is_symlink() or not path.is_dir():
                    raise Refusal(
                        Finding(
                            "directory.required", relative, "Required directory is unavailable."
                        )
                    )
            else:
                read_file(
                    root,
                    relative,
                    limit=2_097_152 if relative.startswith("docs/assets/") else 1_048_576,
                )
        except Refusal as exc:
            report.findings.append(exc.finding)
    for relative in FORBIDDEN_ROOTS:
        path = root / relative
        if path.exists() or path.is_symlink():
            report.findings.append(
                Finding("tree.forbidden", relative, "Forbidden initial source tree is present.")
            )
    try:
        paths = maintained_paths(root)
        for relative in paths:
            if relative.startswith("docs/internal/"):
                report.findings.append(
                    Finding(
                        "private.source", "docs/internal", "Private source entered Git inventory."
                    )
                )
            if relative.endswith((".pyc", ".so", ".whl", ".npz", ".pt", ".ckpt")):
                report.findings.append(
                    Finding("generated.source", ".", "Unexpected generated or large binary source.")
                )
        ignored = read_file(root, ".gitignore").decode("utf-8", errors="strict").splitlines()
        if not {"docs/internal/", "docs/internal/**"}.issubset(ignored) or any(
            line.startswith("!") and "docs/internal" in line for line in ignored
        ):
            report.findings.append(
                Finding(
                    "private.ignore", ".gitignore", "Private documentation ignore policy differs."
                )
            )
    except Refusal as exc:
        report.findings.append(exc.finding)
    except UnicodeError:
        report.findings.append(
            Finding("ignore.encoding", ".gitignore", "Ignore file must be UTF-8.")
        )
    return report
