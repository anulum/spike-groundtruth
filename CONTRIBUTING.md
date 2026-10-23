<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SPIKE-GROUNDTRUTH — repository governance and provenance
-->

# Contributing

Discuss changes with the maintainer at protoscience@anulum.li. Supply the concrete use case, affected contract and an input that can be shared safely. Do not include credentials, private models or confidential training data in an issue or test.

Use Python 3.13.16 and `uv` 0.13.4 to create an isolated `.venv`. Install only the complete hash-locked `requirements-dev.txt`; do not use pip installation, mutable tool upgrades or a different project's environment. Use a shared uv cache on the same filesystem with hardlink mode. A failed hardlink must be resolved before installation continues. Interpreter selection must identify the exact patch, rather than accept a changing default.

Run the native lint, formatter and strict typing commands in [VALIDATION](VALIDATION.md), then the dedicated real-surface tests for changed modules. Every public function has a NumPy-style docstring. Validators refuse missing dependencies, malformed inputs and incomplete outcomes. Do not weaken coverage, suppress a failure or replace a runtime boundary with a mock to obtain acceptance.

Make narrowly scoped changes on local main under the repository's ownership process. New branches, publication, hosted settings, releases and deployments require the maintainer's explicit authority. Review the exact staged paths and diff; retain unrelated work. Hooks must execute. Keep internal plans, operational notes, native histories and reviews outside public source; `docs/internal/` remains ignored and untracked.

Licence headers, JSON sidecars, native API references, command documentation and all implemented counterparts change with the implementation. Describe actual validation and remaining limitations in the proposed change.
