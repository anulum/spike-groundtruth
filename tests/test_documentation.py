# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — native rendering and actual documentation input tests

"""Exercise actual Markdown, links, projections and the real strict site renderer."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from groundtruth_validation.documentation import (
    build_site,
    inspect_markdown,
    inspect_projection,
    render_markdown,
    validate_documentation,
)
from tests.native_process import run_isolated

REPOSITORY = Path(__file__).resolve().parents[1]


def test_actual_strict_native_documentation_through_cli() -> None:
    """Render actual API documentation and inspect the native generated pages."""
    result = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY / "tools/check_documentation.py"),
            "--root",
            str(REPOSITORY),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["reasons"] == []
    assert (REPOSITORY / ".tool-cache/site/validation-tooling/index.html").is_file()


def test_actual_rendered_links_and_invisible_notice(tmp_path: Path) -> None:
    """Accept real heading anchors and file references while excluding comment text."""
    (tmp_path / "linked.md").write_text("# Linked title\n")
    (tmp_path / "image.png").write_bytes(b"finite file reference input")
    (tmp_path / "index.md").write_text(
        "<!-- SPDX-License-"
        "Identifier: hidden -->\n# Own title\n"
        "[own](#own-title) [other](linked.md#linked-title) [web](https://www.anulum.li) "
        "[contact](mailto:protoscience@anulum.li) ![image](image.png) <span>text</span>\n"
    )
    assert inspect_markdown(tmp_path, "index.md") == []
    rendered = render_markdown((tmp_path / "index.md").read_text())
    assert "own-title" in rendered.anchors
    assert "SPDX-License-" + "Identifier:" not in " ".join(rendered.visible)


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("SPDX-License-" + "Identifier: visible", "docs.projection"),
        ("private .coordination/location", "docs.projection"),
        ("[bad](missing.md)", "docs.link"),
        ("[bad](#absent-anchor)", "docs.anchor"),
        ("[bad](LICENSE#absent)", "docs.anchor"),
        ("[bad](https://doi.org/10.0000/unregistered)", "docs.external"),
        ("![bad](https://img.shields.io/badge/unearned)", "docs.external"),
        ("[bad](file:///private)", "docs.external"),
        ("[bad](../outside.md)", "docs.path"),
        ("[bad](/absolute.md)", "docs.path"),
        ("[bad](nul%00name.md)", "docs.path"),
        ("[bad](http://[invalid)", "docs.link"),
    ],
)
def test_document_content_and_reference_refusals(tmp_path: Path, body: str, code: str) -> None:
    """Reject real rendered projection and reference faults with safe locations."""
    (tmp_path / "index.md").write_text("# Index\n\n" + body)
    (tmp_path / "LICENSE").write_bytes((REPOSITORY / "LICENSE").read_bytes())
    assert code in {item.code for item in inspect_markdown(tmp_path, "index.md")}


def test_missing_and_invalid_source_text(tmp_path: Path) -> None:
    """Keep unreadable and non-UTF-8 documentation as explicit failures."""
    assert inspect_markdown(tmp_path, "missing.md")[0].code == "file.unavailable"
    (tmp_path / "invalid.md").write_bytes(b"\xff")
    assert inspect_markdown(tmp_path, "invalid.md")[0].code == "docs.encoding"
    assert validate_documentation(tmp_path).exit_code == 3
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True, timeout=5)
    assert validate_documentation(tmp_path).exit_code == 3


def test_actual_native_renderer_rejects_invalid_configuration(tmp_path: Path) -> None:
    """Use the real installed MkDocs producer against an actually malformed config."""
    broken = tmp_path / "invalid-mkdocs.yml"
    broken.write_text("site_name: [")
    assert build_site(REPOSITORY, broken)[0].code == "docs.build"
    assert build_site(tmp_path, broken)[0].exit_code == 3


def test_actual_empty_environment_lacks_renderer(tmp_path: Path) -> None:
    """Create a real isolated uv environment and require its missing renderer."""
    subprocess.run(
        [
            str(REPOSITORY / ".venv/bin/uv"),
            "venv",
            "--python",
            sys.executable,
            str(tmp_path / ".venv"),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    assert build_site(tmp_path, tmp_path / "mkdocs.yml")[0].code == "docs.build_tool"


def test_missing_markdown_library_in_real_isolated_interpreter() -> None:
    """Invoke the actual documentation command without site-package imports."""
    result = run_isolated(
        REPOSITORY / "tools/check_documentation.py", "--root", str(REPOSITORY), "--json"
    )
    assert result.returncode == 3
    assert "docs.tool" in {item["code"] for item in json.loads(result.stdout)["reasons"]}
    assert result.stderr == ""


def test_actual_projection_parser_rejects_missing_private_and_invalid_html(tmp_path: Path) -> None:
    """Read actual HTML file inputs and refuse missing, private and non-UTF-8 pages."""
    assert inspect_projection(tmp_path)[0].code == "docs.output"
    site = tmp_path / ".tool-cache/site"
    site.mkdir(parents=True)
    (site / "index.html").write_text(
        '<h1 id="index">Index</h1><p>SPDX-License-' + "Identifier: visible</p>"
    )
    assert inspect_projection(tmp_path)[0].code == "docs.projection"
    (site / "index.html").write_bytes(b"\xff")
    assert inspect_projection(tmp_path)[0].code == "docs.output_encoding"
    (site / "index.html").unlink()
    private = site / "internal/note.html"
    private.parent.mkdir()
    private.write_text("<p>Private output path</p>")
    assert inspect_projection(tmp_path)[0].code == "docs.projection"
    private.unlink()
    (site / "linked.html").symlink_to(REPOSITORY / "README.md")
    assert inspect_projection(tmp_path)[0].code == "file.link"
