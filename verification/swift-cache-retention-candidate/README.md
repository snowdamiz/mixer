# Finite isolated Swift cache-retention packet

This packet is not a live integration or full-reactor selection. Read
`../../docs/swift-cache-retention-candidate.md` and `result-summary.json` first:
the synthetic scan benefit coexists with substantial resident-hit overhead.

`baseline-source.tar.gz` and `candidate-source.tar.gz` each contain the complete
132-file finite-test closure. Their individual hashes are in
`baseline-test-manifest.json` and `candidate-manifest.json`; the original unmodified
live input manifest remains `baseline-manifest.json`. The baseline adds only the
common finite trace tests. Candidate product edits affect only copied
`src/experimental/cache/borrowed.rs` and `src/experimental_swift_reactor/cache.rs`.
`implementation.patch` excludes the candidate's test-only inspection seam;
`candidate.patch` includes all product/test changes against the original input.
The two product files remain readable under `overlay/` without extraction.

Run `python3 verify.py` for read-only sealed-member, archive and receipt checks.
`python3 restore-sources.py` restores the two already verified source archives to
previously absent `baseline/` and `candidate/` directories for bounded test reruns.
Use `run.py` with a new command name to retain each rerun. Existing exact argv,
environment, source manifest, stdout/stderr and exit status are under `commands/`.
For example, from the repository root after restoring:

```
python3 verification/swift-cache-retention-candidate/run.py candidate review-cache test --lib --locked --offline --no-default-features --features experimental-swift-reactor --release experimental_swift_reactor::cache_tests:: -- --nocapture --test-threads=1
```

`prepare.py` and `adjust-snapshots.py` document the original one-time transforms;
do not apply them over an already prepared archive. `assess.py` derives the finite
paired measurements. Earlier failed commands and test-only corrections remain
retained. `cleanup.json` describes retired owned scratch. No native, target,
network publication or live-VM command is part of this packet.
