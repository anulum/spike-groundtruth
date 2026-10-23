# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — finite duplicate-free YAML configuration input

"""Read finite YAML mappings without implicit Boolean keys or alias expansion."""

from pathlib import Path
from typing import cast

from groundtruth_validation.inputs import read_file
from groundtruth_validation.report import Finding, Refusal


def read_yaml(root: Path, relative: str) -> dict[str, object]:
    """Read a strict mapping whose scalar values preserve their literal text.

    Parameters
    ----------
    root : Path
        Explicit repository root.
    relative : str
        Authored relative configuration path.

    Returns
    -------
    dict[str, object]
        Mapping with string scalars, list sequences and nested mappings.

    Raises
    ------
    Refusal
        Input or parser is unavailable, duplicate, aliased or malformed.
    """
    try:
        import yaml
        from yaml.events import AliasEvent
        from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
    except ImportError as exc:
        raise Refusal(
            Finding("yaml.tool", ".venv", "Locked YAML parser is unavailable.", 3)
        ) from exc

    def convert(node: Node) -> object:
        """Convert composed nodes while retaining exact string keys and duplicates."""
        if isinstance(node, ScalarNode):
            node.value.encode("utf-8", errors="strict")
            return node.value
        if isinstance(node, SequenceNode):
            return [convert(child) for child in node.value]
        # BaseLoader composition constructs only scalar, sequence and mapping nodes.
        mapping = cast(MappingNode, node)
        result: dict[str, object] = {}
        for key, value in mapping.value:
            if not isinstance(key, ScalarNode) or key.value in result:
                raise ValueError("key")
            key.value.encode("utf-8", errors="strict")
            result[key.value] = convert(value)
        return result

    try:
        text = read_file(root, relative).decode("utf-8", errors="strict")
        if any(isinstance(event, AliasEvent) for event in yaml.parse(text, Loader=yaml.BaseLoader)):
            raise ValueError("alias")
        composed = yaml.compose(text, Loader=yaml.BaseLoader)
        if composed is None:
            raise ValueError("empty")
        parsed = convert(composed)
    except (yaml.YAMLError, ValueError, UnicodeError, RecursionError) as exc:
        raise Refusal(
            Finding("yaml.invalid", relative, "Configuration is not unambiguous finite YAML.", 4)
        ) from exc
    if not isinstance(parsed, dict):
        raise Refusal(Finding("yaml.mapping", relative, "Configuration must be a YAML mapping.", 4))
    return {str(key): value for key, value in parsed.items()}
