# Independent correction review packet

Run `python3 -B verification/swift-memory-promoted-review/verify.py` from any
directory. This checker performs read-only archive, digest, raw-MIR, output,
source-equivalence and focused-results checks. It does not build, execute a
subprocess, recreate scratch or contact a device. Optional `--live-baseline`
checks the historical accepted live source closure and is expected to become
inapplicable after root integration.

`inputs/producer/` is a byte-preserved copy of the frozen correction packet.
Its full 563-file binding map and receipt SHA are checked. `audit.py` and
`reuse_audit.py` independently inspect its source, raw MIR, positive positions,
measured layouts and reused outputs. `review.py` records commands and creates
bounded extracted sources. `finish.py` parses fresh observations and removes
only owned scratch. These authoring scripts write artifacts and are not called
by the read-only checker.

Fresh evidence consists of one exact-candidate Swift unit MIR compilation,
two separately instrumented typed unit layout executions, the three collector
regression tests, and twelve exact-candidate affected-bound selections. Broad
64-memory/184-regression matrices, four prior MIR configurations, sixteen
layouts, eight library checks and Frozen runs are explicitly reused, with
their actual immutable commands, outputs and source bindings.

`failed-attempts/` preserves the failed parser and optional live-checker drafts. No
candidate implementation changed during review. `cleanup.json` records source
revalidation, lsof and scratch removal. `findings.json` accepts only the bounded
correction; root integration, public/native/physical and GA gates remain open.
