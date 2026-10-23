# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — rendered documentation and source-link acceptance

"""Validate rendered Markdown, local references and the real strict native build."""

import posixpath
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from groundtruth_validation.execution import run_tool
from groundtruth_validation.inputs import read_file
from groundtruth_validation.report import Finding, Refusal, Report
from groundtruth_validation.structure import maintained_paths


class References(HTMLParser):
    """Collect actual rendered local references, anchors and visible text."""

    def __init__(self) -> None:
        self.links: list[str] = []
        self.anchors: set[str] = set()
        self.visible: list[str] = []
        super().__init__()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect explicit HTML references and anchor identifiers.

        Parameters
        ----------
        tag : str
            Actual parsed HTML element name.
        attrs : list[tuple[str, str or None]]
            Parsed element attributes, never interpreted as executable code.
        """
        values = dict(attrs)
        anchor = values.get("id")
        if anchor:
            self.anchors.add(anchor)
        reference = (
            values.get("href") if tag == "a" else values.get("src") if tag == "img" else None
        )
        if reference:
            self.links.append(reference)

    def handle_data(self, data: str) -> None:
        """Collect visible text, excluding native invisible HTML comments.

        Parameters
        ----------
        data : str
            Rendered element text from the actual parser.
        """
        self.visible.append(data)


def render_markdown(content: str) -> References:
    """Render Markdown with fixed local extensions and inspect its actual HTML.

    Parameters
    ----------
    content : str
        Decoded Markdown input.

    Returns
    -------
    groundtruth_validation.documentation.References
        References, generated heading anchors and visible text.

    Raises
    ------
    ImportError
        The required locked Markdown renderer is unavailable.
    """
    import markdown

    rendered = markdown.markdown(content, extensions=["toc", "fenced_code", "tables"])
    references = References()
    references.feed(rendered)
    references.close()
    return references


def inspect_markdown(root: Path, relative: str) -> list[Finding]:
    """Check actual rendered content and repository-local files and anchors.

    Parameters
    ----------
    root : Path
        Explicit repository directory.
    relative : str
        Repository-relative source document.

    Returns
    -------
    list[Finding]
        Located content and reference findings, without external network access.
    """
    findings: list[Finding] = []
    try:
        parsed = render_markdown(read_file(root, relative).decode("utf-8", errors="strict"))
        visible = " ".join(parsed.visible)
        if any(
            token in visible
            for token in (
                "SPDX-License-" + "Identifier:",
                ".coordination/",
                "ChatGPT",
                "OpenAI",
                "Codex",
            )
        ):
            findings.append(
                Finding(
                    "docs.projection",
                    relative,
                    "Rendered documentation exposes private or visible provenance text.",
                )
            )
        for reference in parsed.links:
            try:
                parts = urlsplit(reference)
                if parts.scheme or parts.netloc:
                    if parts.scheme not in ("https", "http", "mailto") or any(
                        host in parts.netloc for host in ("shields.io", "doi.org")
                    ):
                        findings.append(
                            Finding(
                                "docs.external",
                                relative,
                                "Unsupported URI or unearned public-service identity.",
                            )
                        )
                    continue
                decoded = unquote(parts.path)
                target = (
                    posixpath.normpath(posixpath.join(posixpath.dirname(relative), decoded))
                    if decoded
                    else relative
                )
                if decoded.startswith("/") or target.startswith("../") or "\0" in target:
                    findings.append(
                        Finding(
                            "docs.path",
                            relative,
                            "Local reference leaves the repository namespace.",
                        )
                    )
                    continue
                raw = read_file(
                    root,
                    target,
                    limit=2_097_152 if target.startswith("docs/assets/") else 1_048_576,
                )
                if parts.fragment:
                    if (
                        not target.endswith(".md")
                        or unquote(parts.fragment)
                        not in render_markdown(raw.decode("utf-8")).anchors
                    ):
                        findings.append(
                            Finding(
                                "docs.anchor",
                                relative,
                                "Local reference names an absent rendered anchor.",
                            )
                        )
            except (Refusal, UnicodeError, ValueError):
                findings.append(
                    Finding(
                        "docs.link",
                        relative,
                        "Local reference cannot resolve to valid repository content.",
                    )
                )
    except ImportError:
        findings.append(
            Finding("docs.tool", ".venv", "Locked Markdown renderer is unavailable.", 3)
        )
    except Refusal as exc:
        findings.append(exc.finding)
    except UnicodeError:
        findings.append(Finding("docs.encoding", relative, "Documentation must be UTF-8."))
    return findings


def build_site(root: Path, configuration: Path) -> list[Finding]:
    """Execute the actual locked renderer with strict owned output boundaries.

    Parameters
    ----------
    root : Path
        Repository owning the actual interpreter and build output.
    configuration : Path
        Explicit authored renderer configuration, never selected by an artifact.

    Returns
    -------
    list[Finding]
        Actual renderer availability or build failures, without raw diagnostics.
    """
    python = str((root / ".venv/bin/python").absolute())
    try:
        probe = run_tool(
            (
                python,
                "-I",
                "-c",
                "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('mkdocs') else 3)",
            ),
            root=root,
            timeout=10,
        )
        if probe.returncode:
            return [
                Finding(
                    "docs.build_tool",
                    "mkdocs.yml",
                    "Locked native documentation renderer is unavailable.",
                    3,
                )
            ]
        child = run_tool(
            (
                python,
                "-I",
                "-m",
                "mkdocs",
                "build",
                "--strict",
                "--clean",
                "--config-file",
                str(configuration.absolute()),
                "--site-dir",
                str((root / ".tool-cache/site").absolute()),
            ),
            root=root,
            timeout=60,
        )
        if child.returncode:
            return [
                Finding("docs.build", "mkdocs.yml", "Strict native documentation rendering failed.")
            ]
    except Refusal as exc:
        return [exc.finding]
    return []


def inspect_projection(root: Path) -> list[Finding]:
    """Inspect actual generated HTML for visible provenance and private content.

    Parameters
    ----------
    root : Path
        Repository containing actual native output under .tool-cache/site.

    Returns
    -------
    list[Finding]
        Actual rendered projection failures; missing generated pages never pass.
    """
    findings: list[Finding] = []
    site = root / ".tool-cache/site"
    pages = sorted(site.rglob("*.html"))
    if not pages:
        return [
            Finding(
                "docs.output", "mkdocs.yml", "Native renderer did not produce actual HTML pages.", 3
            )
        ]
    for page in pages:
        try:
            relative = page.relative_to(root).as_posix()
            rendered = References()
            rendered.feed(read_file(root, relative).decode("utf-8", errors="strict"))
            visible = " ".join(rendered.visible)
            if page.relative_to(site).parts[0] == "internal" or any(
                token in visible
                for token in (
                    "SPDX-License-" + "Identifier:",
                    ".coordination/",
                    "ChatGPT",
                    "OpenAI",
                    "Codex",
                )
            ):
                findings.append(
                    Finding(
                        "docs.projection",
                        "mkdocs.yml",
                        "Actual rendered pages expose private or visible provenance content.",
                    )
                )
        except Refusal as exc:
            findings.append(exc.finding)
        except UnicodeError:
            findings.append(
                Finding(
                    "docs.output_encoding", "mkdocs.yml", "Native generated HTML must be UTF-8."
                )
            )
    return findings


def validate_documentation(root: Path) -> Report:
    """Validate source links, execute the strict renderer and inspect actual HTML.

    Parameters
    ----------
    root : Path
        Repository with its own locked development environment.

    Returns
    -------
    Report
        Scoped documentation result; missing or failed rendering never passes.
    """
    report = Report("documentation", [])
    try:
        paths = maintained_paths(root)
        documents = sorted({"README.md", "docs/index.md"} | {p for p in paths if p.endswith(".md")})
        for relative in documents:
            report.findings.extend(inspect_markdown(root, relative))
        failures = build_site(root, root / "mkdocs.yml")
        report.findings.extend(failures)
        if not failures:
            report.findings.extend(inspect_projection(root))
    except Refusal as exc:
        report.findings.append(exc.finding)
    return report
