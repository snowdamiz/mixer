# Unselected adaptive-retention specification and finite model

Root withheld implementation selection after the finite model showed a phase
change decode regression and appreciable added policy costs. This is neither an
implemented candidate rejection nor a VM/full-target result. No policy retuning
occurred after observing these outcomes.

- Specification: `docs/swift-adaptive-retention-design.md`.
- Executable finite model: `model.py`; run through `python3 verification/swift-adaptive-retention-design/verify.py`.
- Raw model stdout: `stdout.json`; raw stderr: `stderr.txt`.
- Per-command version/platform/scope/source receipt: `receipt.json`.
- Consulted source hashes: `source-manifest.json`.
- Exact packet members and hashes: `seal.json`.

The six existing access sequences and a 256-resident-hit control execute against
both an ordinary LRU policy model and the new adaptive policy model. Seventeen
controls cover capacities, pins, multiple victims, failure boundaries, timestamp
checks, deterministic ties and phase turnover. Warm-up is excluded equally from
trace interval observations. Decode bodies and work differences from their sizes
are not executed. Proposed Rust field layout, named-value reservation totals,
ghost hash-link implementation, actual CacheWork, elapsed time, the full target,
native/device behavior and all external acceptance gates remain unverified.

`estimated_added_*` fields apply the authored policy schedule to model decisions
and valid-chain bucket occupancies. They exclude existing engine paths and build
costs. They are estimates, not observed VM work. The hit-budget sensitivity uses
the original failure's parent-supplied hit and repeated-build attribution counts;
it does not forecast candidate instruction progress.

The only external algorithm source consulted was the original
[FAST 2003 ARC paper](https://www.usenix.org/legacy/events/fast03/tech/full_papers/megiddo/megiddo.pdf),
Figure 4 and section IV. The proposal changes directory trimming/history,
variable-size replacement, pins and failure commits. It does not claim canonical
ARC behavior or import any implementation/dependency.
