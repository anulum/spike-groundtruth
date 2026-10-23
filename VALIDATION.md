<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SPIKE-GROUNDTRUTH — repository governance and provenance
-->

# Validation

Every report contains `gate`, `scope`, `status` and `reasons`. Scope is `local_scaffold_infrastructure`. Exit 0 means the requested operation passed; 2 means refused input or policy; 3 means a required environment, file or output is unavailable; 4 means invalid invocation or configuration. When multiple findings exist, precedence is 4, then 3, then 2. Findings retain every observed cause and use authored locations and safe text.

## Metadata

```sh
.venv/bin/python tools/check_repository_metadata.py --root . --json
```

This operation checks strict UTF-8 JSON, duplicate keys, nonfinite numbers, closed schema shape, independent schema identity, exact project/profile, actual Python version, semantic Python range and the raw lock SHA-256. It does not require a generated capability inventory. Missing libraries are unavailable, never skipped.

## Inventory

```sh
.venv/bin/python tools/check_repository_inventory.py --root . --mode generate --output NEW-INVENTORY.json --json
.venv/bin/python tools/check_repository_inventory.py --root . --mode verify --json
```

Generation requires a new repository-relative output, accepted metadata and a usable output directory. It publishes complete deterministic bytes exclusively; collisions leave existing bytes unchanged. Verification requires canonical `capability-inventory.json` and the complete required repository paths. Generating an inventory does not establish complete repository readiness. Inventory data has no self-digest and grants no domain qualification.

## Native quality checks

```sh
.venv/bin/ruff check tools tests
.venv/bin/ruff format --check tools tests
.venv/bin/mypy --strict tools tests
```

Run dedicated test modules for each changed implementation through pytest and coverage. Statement and branch thresholds are 100 percent. Real CLI, file, interpreter and report-write failures are exercised. A command's documentation is not evidence that its current source revision passed; retain actual scoped verification results separately from public capability declarations.

## Source, workflow, dependency and documentation checks

```sh
.venv/bin/python tools/check_source_provenance.py --root . --json
.venv/bin/python tools/check_workflow_policy.py --root . --json
.venv/bin/python tools/check_dependency_alignment.py --root . --json
.venv/bin/python tools/check_documentation.py --root . --json
```

Source provenance checks actual maintained notices, exact JSON sidecars, legal text and licensed image identities. Workflow policy checks every declared job, trigger, read-only action, verified source pin and stable aggregate outcome. Dependency alignment reconciles the complete lock, actual installed producers, local hooks and native release payloads. Documentation executes strict native rendering and inspects actual generated HTML as well as source links.

## Explicit native setup and resource bounds

`make native-tools` explicitly downloads the exact release archives, verifies archive SHA-256, extracts only the named executable, verifies its payload SHA-256 and removes its temporary archive. Native tools remain under ignored `.tool-cache/native/`. Their expected sources, versions and licences are recorded in `native-tool-provenance.json`. Validators have no automatic installation or network fallback.

The official Gitleaks executable reserves four GiB of virtual address space for its regular-expression runtime. A virtual-address limit below that reserve prevents startup; reserve physical memory separately. Linux user scopes can cap an owned verification job with `MemoryMax=768M`, `CPUQuota=100%` and `TasksMax=64`; `GOMEMLIMIT=512MiB` and `GOMAXPROCS=1` further constrain the Go runtime. This is a local resource profile, not physical-device or hostile operating-system qualification.

## Preflight and actual check scope

```sh
.venv/bin/python tools/preflight.py --root . --profile local-scaffold --json
.venv/bin/python tools/preflight.py --root . --check metadata --check dependencies --json
```

The default profile contains actual required guards, native lint/format/types/docstrings, REUSE, all-severity static analysis, workflow syntax/security, complete locked dependency audit, source secret scanning, installed compatibility, a reproducible development SBOM and infrastructure tests. Run full preflight only under reserved resources or the authorised CI/pre-push process. Normal local commits use the corresponding focused checks and staged-source review. A named subset reports `preflight_scoped`; it cannot establish complete profile acceptance.

Preflight retains each attempted check's actual return code and stable reason identifiers. A missing environment has unavailable results with unobserved exits, rather than inferred passes. Plain text from a native version command cannot stand in for a checker report. Failures remain visible while subsequent required checks run.
