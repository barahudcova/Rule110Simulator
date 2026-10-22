# Sources and acknowledgments

This document identifies the work, software, and tools used to develop this
project.

The renderer, camera, and menu widgets derive from
[PyCA](https://github.com/frotaur/PyCA), originally developed by Vassilis
Papadopoulos. 

The simulation follows Matthew Cook's
[2004 universality construction](https://www.complex-systems.com/abstracts/v15_i01_a01/)
and [2009 concrete construction](https://arxiv.org/abs/0906.3248), with the
revised consecutive-empty-appendant components designed by Barbora Hudcová.
The binary glider catalogue retains her manually constructed patterns. The
program phase tables implement the fixed geometric joins used by the encoder.

The finite patterns used to recognize stationary data, moving data, and
ossification were generated in this project from Rule 110 collision
simulations and phase-aligned glider patterns.
The recognition catalogues and spacing data are included
in `pyca_verifier/data/`; `catalogue_manifest.json` records their hashes.
`source.json` identifies the historical source snapshot, rather than the
current package as a whole.

## AI assistance

The original Rule 110 implementation was developed by Barbora Hudcová.
This version was developed with assistance from OpenAI's ChatGPT and Codex
in constructing and checking collision catalogues, developing the decoder,
optimizing performance, and preparing documentation. Responsibility for the
released implementation and its mathematical claims remains with the author.

## Licensing

These credits do not change any licenses applying to the original code or
assets. This project currently declares no license.
