# Explicit stdio ownership correction

contract.md defines the C01 raw descriptor lifecycle, name/close uncertainty,
destructor safety and exact pending qualifications. control-adaptations.md keeps
the literal failing witness separate from the replacement's labeled fault boundary.

Only new/replay/corrected/replay/prototype.py changes between variants. It owns
two raw temporary descriptors explicitly, captures births before later hooks,
removes automatic file-object destructors, preserves original primary/result and
all cleanup failures, and reports every unresolved obligation as nonhealthy.

Run python3 -B run_evidence.py here. It records both producer26-method replays,
ten independent positive replays, two literal raw C01 attempts, the unchanged142
lifecycle cases and57 new stdio cases. Read receipt.json/results.json/raw logs for
exact counts, failures, source/tool identity and separate cleanup dispositions.
The seal includes every file plus declared exact76-byte self-seal metadata.

All code is host preparation. Real OS ambiguity retirement, Rust provenance/
context/accounting, canonical integration, native/UI/capture/full-target/FieldLog/
OTA/GA remain pending. No frozen packet, canonical source or runtime limit is
changed; no commit, push, process inventory or production publication occurs.
