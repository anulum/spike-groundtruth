<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SPIKE-GROUNDTRUTH — repository governance and provenance
-->

# Validation tooling API

The metadata command accepts `--root` and `--json`. The inventory command additionally accepts `--mode generate|verify` and requires `--output` only for generation. All commands emit safe structured JSON. Exits are 0 for the requested scope, 2 for refusal, 3 for unavailable required inputs or tools, and 4 for invalid invocation or configuration.

Metadata validation accepts no generated inventory dependency. Inventory generation publishes deterministic new bytes; verification requires the canonical inventory and complete initial paths. A successful operation does not qualify stimulus correctness or regeneration or establish release readiness.

## Metadata acceptance

::: groundtruth_validation.metadata.validate_metadata

## Finite input

::: groundtruth_validation.inputs.read_file

::: groundtruth_validation.inputs.read_json

## Capability inventory

::: groundtruth_validation.capabilities.inventory_bytes

::: groundtruth_validation.capabilities.create_inventory

::: groundtruth_validation.capabilities.validate_capabilities

## Diagnostics

::: groundtruth_validation.report.Finding

::: groundtruth_validation.report.Report

## Command interfaces

::: groundtruth_validation.cli.metadata_main

::: groundtruth_validation.cli.inventory_main

## Source ownership and maintained tree

::: groundtruth_validation.provenance.validate_notice

::: groundtruth_validation.provenance.validate_provenance

::: groundtruth_validation.structure.maintained_paths

::: groundtruth_validation.structure.validate_structure

## YAML and workflow policy

::: groundtruth_validation.yaml_input.read_yaml

::: groundtruth_validation.workflows.validate_workflows

## Complete dependency observations

Release candidates and observed installed metadata are separate records. The hash lock covers the entire selected development graph. Exact source-builder constraints also use that lock. Recorded installation RECORD hashes are observations; relocated entry-script paths prevent treating them as universal build identities. Custom licence references retain exact source terms and do not infer permissions.

::: groundtruth_validation.dependency_lock.parse_direct

::: groundtruth_validation.dependency_lock.parse_lock

::: groundtruth_validation.dependency_records.Artifact

::: groundtruth_validation.dependency_records.LicenseEvidence

::: groundtruth_validation.dependency_records.LicenseSource

::: groundtruth_validation.dependency_records.PackageRecord

::: groundtruth_validation.dependency_records.read_provenance

::: groundtruth_validation.dependencies.verify_records

::: groundtruth_validation.dependencies.verify_installed

::: groundtruth_validation.dependencies.verify_configuration

::: groundtruth_validation.dependencies.validate_dependencies

::: groundtruth_validation.native_tools.verify_native_tools

## Actual documentation rendering

::: groundtruth_validation.documentation.References

::: groundtruth_validation.documentation.render_markdown

::: groundtruth_validation.documentation.inspect_markdown

::: groundtruth_validation.documentation.build_site

::: groundtruth_validation.documentation.inspect_projection

::: groundtruth_validation.documentation.validate_documentation

## Tool completion and scoped preflight

Every tool uses a fixed absolute executable, literal arguments and a finite deadline. Actual exits survive communication errors where observed. Output limits apply to accepted completed output; the caller reserves process memory separately. A named preflight subset reports its narrower scope. The complete operation requires the entire compiled profile. Missing tools, invalid protocol and native failures retain their real states.

::: groundtruth_validation.execution.ToolResult

::: groundtruth_validation.execution.run_tool

::: groundtruth_validation.preflight.Check

::: groundtruth_validation.preflight.Outcome

::: groundtruth_validation.preflight.PreflightReport

::: groundtruth_validation.preflight.validate_checker_report

::: groundtruth_validation.preflight.run_check

::: groundtruth_validation.preflight.run_checks

::: groundtruth_validation.preflight.source_payload

::: groundtruth_validation.validation_profile.scaffold_checks

::: groundtruth_validation.preflight_cli.preflight_main

## Shared command and protocol interfaces

::: groundtruth_validation.inputs.parse_json

::: groundtruth_validation.report.Refusal

::: groundtruth_validation.cli.Parser

::: groundtruth_validation.cli.check_main

::: groundtruth_validation.cli.emit_report

::: groundtruth_validation.ci_dependencies.verify_ci_dependencies

## Native workflow composition

The coordinator executes the eight complete native jobs from the maintained workflow sources. Each of four category gates requires every actual descendant result, and the stable required gate checks all four category results. The workflow policy verifies exact job equality with each source and rejects missing descendants, masked outcomes, altered commands and workflow calls. This preserves all category checks without depending on an unsupported reusable-workflow syntax. Both native syntax and unchanged pedantic workflow checks inspect the actual executable configuration; no projected input or suppressed finding is used.
