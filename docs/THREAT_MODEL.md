<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SPIKE-GROUNDTRUTH — repository governance and provenance
-->

# Tooling trust boundaries

Assets are the maintained repository source, exact descriptor and lock identities, and truthful infrastructure reports. The maintainer-controlled executable policy and its independently pinned schema are trusted. Received JSON values are data and cannot select an executable, plugin, repository identity or weaker schema.

The input boundary refuses duplicate keys, nonfinite numbers, invalid UTF-8, unpaired Unicode surrogates, excessive input size, linked inputs and nonregular files. Diagnostics use fixed authored messages. An unknown input or unavailable dependency cannot become a pass. Generation requires accepted source metadata and creates a caller-chosen new relative file exclusively; verification never rewrites the canonical inventory.

The tools assume an ordinary stable local filesystem and reviewed executable environment. They do not provide a sandbox against concurrent hostile filesystem changes, operating-system compromise, power loss or malicious modifications to their own reviewed source. Static checks do not prove generator correctness, independent truth validity, bit-exact regeneration or physical provenance. Those require separately qualified domain producers, trust policy and consumers.
