# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — source provenance command

"""Validate actual maintained source notices and licence identities."""

from groundtruth_validation.cli import check_main
from groundtruth_validation.provenance import validate_provenance

raise SystemExit(check_main("source_provenance", validate_provenance))
