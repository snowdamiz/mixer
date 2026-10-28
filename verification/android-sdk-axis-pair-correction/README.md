# Reviewed SDK source-pair correction

Current remote SDK132 and all nine multiline methods pass at56ff14c. The same
job later fails31 CLI tests with32 issues because exact source-pair4 still
expects the previous Authoring.swift/Validation.swift bytes. No source admission
was weakened or skipped by that failure.

The new exact distribution identity mixer.android-source-pair.5 selects only
those two already-reviewed source changes. The other20 SDK files, all23 native
adapter files, descriptor, wire contracts and source admission implementation
remain unchanged. The Swift policy, generated driver ID check and expected
policy test agree. Existing Swift and Python legacy-profile matrices now also
reject profile4, without accepting local lock recomputation or source drift.
This distribution identifier is unrelated to the held Android candidate-v5;
that actor, its files and its evidence were not retried or modified.

Eight in-process production admission controls pass under subprocess, socket
and custody audit denial. They include three existing methods and five
source/profile integrity probes. Full Swift CLI and Python child-entrypoint
suites remain for remote CI. No compiler, native renderer, emulator or phone
was launched. Host admission is not an Android/native/release/GA receipt.

The first control-runner import failed before running tests because select.py
shadowed the standard-library module. Its one-shot guard prevented mutation.
The script was renamed without replay; the failure and final eight-test output
remain in this packet.
