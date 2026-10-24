# Frozen bounded promoted accounting correction

Run `python3 -B verification/swift-memory-promoted-correction/verify.py`.
The checker reads only archived evidence. `--live-baseline` adds the live control
closure check. Candidate/metadata source archives are authoritative; session
scratch paths are historical and are removed. Reproduce only in a fresh unsealed
copy with a fresh uniquely owned scratch; never modify a frozen packet.

The final source has eight new unit accounting fields only. Historical schema
rows retain their original provenance; canonical-audit.json records fresh actual
compiler locations and exact role matches in four configurations. Runtime and
layout commands have distinct archived source identities. Frozen runtime results
are explicitly reused with exact source-equivalence evidence, not rerun here.
Fresh independent correction review and root acceptance remain pending.
