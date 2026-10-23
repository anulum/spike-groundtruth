# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SPIKE-GROUNDTRUTH — strict documentation command

"""Check actual rendered documentation and execute the strict native build."""

from groundtruth_validation.cli import check_main
from groundtruth_validation.documentation import validate_documentation

raise SystemExit(check_main("documentation", validate_documentation))
