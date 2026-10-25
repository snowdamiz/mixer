# Frozen V2 repair review handoff

This is an isolated replacement candidate, not accepted or integrated source.
Read `docs/hosted-worker-controller-v2.md` and `receipt.json` first. Preserve the
entire packet before replay; independent review should use its own output lane.

`candidate/` is the 60-record copied producer closure with bounded R1/R2 changes.
`source-manifest.json` and `source-snapshot.tar.gz` seal the final candidate.
`candidate.diff` lists every original-to-V2 source/compiled/fixture change.
`assertion-preservation.json` proves unchanged original and independent test
bodies. `inputs/` retains consulted source/fixtures, original rejected packets,
all prior bound artifacts and official output-gate documentation. Dependency and
runtime bytes are hash-bound in the copied manifests; they are not newly installed.
`input-closure-manifest.json`/`input-closure.tar.gz` seal every consulted frozen
input plus owned replay/verification code. Original producer/review directories
are unchanged. Each `runs/` entry retains command, exact source/archive, output,
report and cleanup evidence. Baseline regression exit 1 is intentional evidence.

The original frozen producer input archive is byte-identical, and an independent
verifier can extract it and compare the final source diff before executing code.
Source-tree digests in V2 use sorted records of path, bytes and SHA-256 with compact
sorted-key JSON. Original producer's different record shape (including modes)
retains its separate original digest. Do not confuse those two hash domains.

The commands below replay into newly named owned run folders. To keep this frozen
packet immutable, copy its files and use `run.py` from that copied packet. The
runner still verifies/copies original pinned dependencies under the selected
workspace root, then removes only its exact scratch and test storage. Existing
run names are refused. Every dependency installation, if necessary in a separate
review environment, must be separately recorded and use
`npm ci --ignore-scripts --no-audit --no-fund` with the frozen lockfile.

```sh
python3 run.py fresh-build build
python3 run.py fresh-producer producer
python3 run.py fresh-regressions regressions
python3 run.py fresh-focused focused
python3 run.py fresh-noncooperative noncooperative
python3 run.py fresh-closure closure
python3 run.py fresh-inventory inventory
```

`prepare.py` documents the verified initial extraction and refuses an existing
candidate. `repair.py` is the historical initial R1/R2 edit, not a replay command
for the final tree; later authorized migration/stop/fixture edits are completely
captured in `candidate.diff` and each exact run snapshot. Use the frozen candidate
for independent replay. `freeze.py` seals/checks this packet; `verify_final.py`
checks its immutable receipt/archive bindings without running product code.

No provider deployment, runner ingress, real clock qualification, pending registry,
restore anchor, public authorization, signing/store/customer/GA acceptance or
physical-device qualification follows from these local tests.
