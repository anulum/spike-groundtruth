# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — repository validation tooling

PYTHON := .venv/bin/python
.DEFAULT_GOAL := metadata
.PHONY: metadata inventory source workflows dependencies docs lint types preflight
metadata:
	$(PYTHON) tools/check_repository_metadata.py --root . --json
inventory:
	$(PYTHON) tools/check_repository_inventory.py --root . --json
source:
	$(PYTHON) tools/check_source_provenance.py --root . --json
workflows:
	$(PYTHON) tools/check_workflow_policy.py --root . --json
dependencies:
	$(PYTHON) tools/check_dependency_alignment.py --root . --json
docs:
	$(PYTHON) tools/check_documentation.py --root . --json
lint:
	$(PYTHON) -m ruff check tools tests
	$(PYTHON) -m ruff format --check tools tests
types:
	$(PYTHON) -m mypy --strict tools tests
preflight:
	$(PYTHON) tools/preflight.py --root . --profile local-scaffold --json

.PHONY: native-tools
native-tools:
	mkdir -p .tool-cache/native/actionlint
	curl --fail --location --silent --show-error --max-time 60 --output .tool-cache/native/actionlint.tar.gz https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_linux_amd64.tar.gz
	printf '%s\n' '8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8  .tool-cache/native/actionlint.tar.gz' | sha256sum --check --status
	tar -xzf .tool-cache/native/actionlint.tar.gz -C .tool-cache/native/actionlint actionlint
	printf '%s\n' 'c872d6db8c6bf83a8eaa704fc93999f027d55dffbc63b8a6abdccb47df5f4cd4  .tool-cache/native/actionlint/actionlint' | sha256sum --check --status
	rm -- .tool-cache/native/actionlint.tar.gz
	mkdir -p .tool-cache/native/gitleaks
	curl --fail --location --silent --show-error --max-time 60 --output .tool-cache/native/gitleaks.tar.gz https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz
	printf '%s\n' '551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb  .tool-cache/native/gitleaks.tar.gz' | sha256sum --check --status
	tar -xzf .tool-cache/native/gitleaks.tar.gz -C .tool-cache/native/gitleaks gitleaks
	printf '%s\n' '88f91962aa2f93ac6ab281d553b9e125f5197bbbce38f9f2437f7299c32e5509  .tool-cache/native/gitleaks/gitleaks' | sha256sum --check --status
	rm -- .tool-cache/native/gitleaks.tar.gz
