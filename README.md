<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SPIKE-GROUNDTRUTH — repository governance and provenance
-->

# SPIKE-GROUNDTRUTH

SPIKE-GROUNDTRUTH defines the boundary for reproducible synthetic event-vision, audio and industrial-control stimuli with explicit model truth. The current implementation provides repository validation tooling. Generators, independent truth checks, container output, quality integration and whole-byte regeneration are planned; no stimulus-generation package or qualified scientific capability is installed.

SPIKE-GROUNDTRUTH is part of the **SC Neuromorphic Computing Systems** group (SC-NEUROMORPHIC-COMPUTING-SYSTEMS). The [group and project map](https://github.com/anulum/sc-neurocore/blob/main/docs/ecosystem.md) shows the whole programme and where this repository sits in it.

The local metadata explicitly records `local_scaffold`, `architecture_only`, empty capabilities, claims and qualified schemas. The planned identifier `groundtruth_stimulus.manifest.v1` is a declaration, not a registered or accepted evidence format.

## Validate repository metadata

Use Python 3.13.16 with the hash-locked development dependencies:

```sh
uv venv --python 3.13.16 .venv
uv pip install --python .venv/bin/python --require-hashes --build-constraints requirements-dev.txt --default-index https://pypi.org/simple -r requirements-dev.txt
make native-tools
.venv/bin/python tools/check_repository_metadata.py --root . --json
```

The metadata checker binds the exact reviewed schema, expected repository identity, governing profile, running interpreter and raw development lock. A metadata pass covers that operation only. Repository inventory verification additionally requires the complete initial path contract.

Read [validation](VALIDATION.md), [architecture](ARCHITECTURE.md), [contribution instructions](CONTRIBUTING.md) and [support](SUPPORT.md). The [roadmap](ROADMAP.md) distinguishes planned domain work from implemented tooling.

## Licence and contact

AGPL-3.0-or-later applies; see [LICENSE](LICENSE) and [NOTICE](NOTICE.md). Commercial licensing is available through [ANULUM](https://www.anulum.li), protoscience@anulum.li. No hosted repository, deployment, release, badge, DOI or certification is asserted by this local source tree.

![ANULUM](docs/assets/anulum_logo_company.jpg)

![Fortis Studio](docs/assets/fortis_studio_logo.jpg)

The reservation below was issued on 2026-10-19 and added to this repository on 2026-10-23.

## Text and data mining reservation

The rightsholder, Miroslav Šotek (ANULUM), expressly reserves the use of the
works in this repository for text and data mining, including the collection of
this content for, and its use in, training, fine-tuning or evaluating machine
learning and artificial intelligence models, in accordance with Article 4(3) of
Directive (EU) 2019/790 and the national provisions transposing it.

No permission for such use has been granted beyond what the licence in
`LICENSE` grants. This reservation does not change that licence: uses the
licence permits remain permitted on its terms, including its attribution and
share-alike conditions.

Reservation made on 2026-10-19. Requests for permission: contact the
rightsholder through the contact listed in this repository.
