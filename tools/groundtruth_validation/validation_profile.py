# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — fixed local-scaffold execution profile

"""Declare actual required commands without data-driven tool or plugin selection."""

from pathlib import Path

from groundtruth_validation.preflight import Check


def scaffold_checks(root: Path) -> tuple[Check, ...]:
    """Resolve the complete literal local-scaffold tool sequence for one root.

    Parameters
    ----------
    root : Path
        Explicit repository directory with its own locked environment.

    Returns
    -------
    tuple[Check, ...]
        Required real checker, native quality, audit, test and inventory tools.
        No unavailable tool is omitted and no artifact selects an executable.
    """
    root = root.absolute()
    python = str(root / ".venv/bin/python")
    definitions = (
        ("metadata", "check_repository_metadata.py", "repository_metadata"),
        ("source", "check_source_provenance.py", "source_provenance"),
        ("workflows", "check_workflow_policy.py", "workflow_policy"),
        ("dependencies", "check_dependency_alignment.py", "dependency_alignment"),
        ("documentation", "check_documentation.py", "documentation"),
        ("inventory", "check_repository_inventory.py", "repository_inventory"),
    )
    checks = [
        Check(
            name,
            (python, str(root / "tools" / filename), "--root", str(root), "--json"),
            "tools/" + filename,
            90,
            gate,
        )
        for name, filename, gate in definitions
    ]
    checks.extend(
        (
            Check(
                "lint",
                (python, "-I", "-m", "ruff", "check", "tools", "tests"),
                "pyproject.toml",
                60,
                module="ruff",
            ),
            Check(
                "format",
                (python, "-I", "-m", "ruff", "format", "--check", "tools", "tests"),
                "pyproject.toml",
                60,
                module="ruff",
            ),
            Check(
                "types",
                (python, "-I", "-m", "mypy", "--strict", "tools", "tests"),
                "pyproject.toml",
                180,
                module="mypy",
            ),
            Check(
                "docstrings",
                (python, "-I", "-m", "ruff", "check", "--select", "D", "tools", "tests"),
                "pyproject.toml",
                60,
                module="ruff",
            ),
            Check(
                "licences", (python, "-I", "-m", "reuse", "lint"), "REUSE.toml", 60, module="reuse"
            ),
            Check(
                "static-security",
                (
                    python,
                    "-I",
                    "-m",
                    "bandit",
                    "--ini",
                    "/dev/null",
                    "--ignore-nosec",
                    "--severity-level",
                    "all",
                    "--confidence-level",
                    "all",
                    "-r",
                    "tools",
                    "-q",
                ),
                "tools",
                90,
                module="bandit",
            ),
            Check(
                "workflow-syntax",
                (str(root / ".tool-cache/native/actionlint/actionlint"), "-color=false"),
                ".github/workflows",
                60,
            ),
            Check(
                "workflow-security",
                (
                    str(root / ".venv/bin/zizmor"),
                    "--offline",
                    "--no-progress",
                    "--persona",
                    "pedantic",
                    "--min-severity",
                    "informational",
                    ".github/workflows",
                ),
                ".github/workflows",
                60,
            ),
            Check(
                "dependency-audit",
                (
                    str(root / ".venv/bin/pip-audit"),
                    "-r",
                    "requirements-dev.txt",
                    "--disable-pip",
                    "--no-deps",
                    "--cache-dir",
                    str(root / ".tool-cache/pip-audit"),
                ),
                "requirements-dev.txt",
                180,
            ),
            Check(
                "secret-scan",
                (
                    str(root / ".tool-cache/native/gitleaks/gitleaks"),
                    "stdin",
                    "--config",
                    "gitleaks.toml",
                    "--ignore-gitleaks-allow",
                    "--gitleaks-ignore-path",
                    "/dev/null",
                    "--redact",
                    "--no-banner",
                    "--timeout",
                    "60",
                ),
                ".",
                90,
                source_stdin=True,
            ),
            Check(
                "installed-compatibility",
                (str(root / ".venv/bin/uv"), "pip", "check", "--python", python),
                ".venv",
                30,
            ),
            Check(
                "sbom",
                (
                    str(root / ".venv/bin/cyclonedx-py"),
                    "environment",
                    python,
                    "--output-reproducible",
                    "--of",
                    "JSON",
                    "-o",
                    ".tool-cache/development-sbom.json",
                ),
                "requirements-dev.txt",
                90,
            ),
            Check(
                "tests",
                (
                    python,
                    "-I",
                    "-m",
                    "pytest",
                    "tests",
                    "--cov",
                    "--cov-report=term-missing",
                    "--cov-report=json:.tool-cache/coverage/report.json",
                ),
                "tests",
                300,
                module="pytest",
            ),
        )
    )
    return tuple(checks)
