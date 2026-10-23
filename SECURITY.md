<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SPIKE-GROUNDTRUTH — repository governance and provenance
-->

# Security reporting

Report suspected vulnerabilities privately to protoscience@anulum.li with the affected revision, reproducible command, observed result and expected boundary. Do not send live credentials, private training data or exploit output containing secrets. The maintainer coordinates investigation and disclosure; no guaranteed response deadline is asserted.

The current supported surface is local repository validation tooling. There is no released stimulus-generation runtime, deployed endpoint, hosted security service or certification. The tooling checks static repository inputs and safe diagnostics. It is not a sandbox for concurrent hostile filesystem mutation. See the [threat model](docs/THREAT_MODEL.md) for assumptions and residual risks.
