# Candidate 4: corrected source-bound construction qualification

Candidate 2's main qualification commands used candidate 1's cwd. Candidate 3
corrected the binding, passed its library tests, and stopped at actual-source
Clippy failures. Both histories remain unchanged. This candidate includes only
the root's admission-test correction and five targeted lint annotations, with
no constructor field, body, allocation or accounting change. The exact diff is
`source-delta.json` and `annotation-only.patch`.

The receipt binds 425 VM inputs, the archive and all command/log hashes.
Every command resolves cwd at runtime, checks the snapshot before and after,
and gives Cargo an explicit absolute manifest. `cwd-audit.json` preserves that
per-command evidence; it cannot silently use either older candidate directory.

Both profiles pass 14 narrow construction tests, 7 original layout tests, and
six library feature configurations (7 / 13 / 122 / 122 / 122 / 151). Both
Clippy modes, formatting and external-constructor privacy rejection pass.
Full all-feature host regression passes 367 tests with
9 ordinary ignored tests per profile. The ignored tests
remain pending. Eight production/unit, Debug/Release, minimal/combined metadata
configurations agree with the approved logical bounds: production foundation
267,800 / additional construction 1,062,312 / same header 207,352; unit
268,336 / 1,065,072 / 208,312. These are logical accounting inventories, not
physical stack or RSS measurements.

The independent exact-type map remains in the immutable candidate2-api review
proposal. Product source contains no metadata probes or public construction
route. The archive creates no initialized/Ready reactor and executes no target.
Independent root acceptance, full frozen executor acceptance, interpreter,
initialize/invoke, growth/active-frame unwind/exhaustive interruption, full
target, physical devices, immutable published FieldLog, signing/store/customer/
operational and GA gates remain pending. No commit/push/tracker change is made
by this producer lane.
