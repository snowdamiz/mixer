# Apple keyboard full-case V2 independent source and host review

V2 remains **changes-required** because a bounded allocation-failure control
found an owned workspace leak and a false cleanup receipt. Both original V1
findings are repaired. This review binds V2 producer seal
`3a17071cc13bada8e47c48d2b739289ac9210ecacb90935e016a1ea4ce5a14d4`
and all 77 sealed files. Native compilation/execution remain unselected.

**P2 R3: allocation failure falsely passes owned workspace removal.**
The new `orchestration.py` line 66 allocates the fresh workspace and then calls
`chmod` and `stat`. Its durable identity is assigned into the lifecycle only on
line 67. If `chmod` fails, the allocated path exists but that lifecycle identity
is absent. The registered cleanup at line 88 calls inherited `remove_ephemeral`,
which returns successfully when the identity is absent. All five cleanup rows
then report passed, including workspace removal, while the owned directory
remains. The first OSError is retained and the run remains failed; the synthetic
simulator, real loopback server, and thread do clean up. This is a resource leak
and false cleanup receipt, not a native interaction pass.

`allocation_probe.py` injects that precise chmod failure into the actual composed
`h.run`, with all native/Popen boundaries mocked and a real loopback lifetime.
`allocation-failure.json` retains the still-present path and all five passed
cleanup rows. The review archives the leaked empty directory with its mode and
then removes owned scratch, recording recovery in `cleanup.json`. A correction
must bind ownership at allocation or otherwise clean/reconcile a partially
initialized workspace without reporting a missing identity as successful
removal. Preserve the first exception and the existing strict ownership checks.

The exact V1 durable preload now rejects before the harness import and leaves
the historical module unchanged. Every one of the 23 closed import aliases
rejects an outside preload. Independent controls also reject post-composition
substitution before new Bridge output, verify sticky rejection through the
actual HTTP endpoint after cache restoration, and reject case-data origin
redirection without modifying any producer file. The independently observed
normal and repeated legacy-load closure matches 20 loaded source files plus
four data reads. The selection binds 21 source files and three case-data files;
the offline replay helper is selected but not loaded on the normal path.

The exact V1 export-reporting fault now attempts all five cleanup operations,
leaves no synthetic workspace/thread behind, and preserves the original strict
XCTest ValueError. Additional independent controls preserve the identical first
KeyboardInterrupt object through unavailable command/final receipts and each
of the five cleanup operations failing after its real action. They execute the
inherited owned-simulator cleanup against a mocked process ledger, verify
shutdown/delete/reconciliation, and preserve a baseline synthetic instance.
New normal commands remain blocked after reporting uncertainty while cleanup
commands retain their observed status. No native process was launched.

The final matrix has 37 passing host methods: nine retained oracle methods,
four retained Bridge/witness methods, 13 ported independent V1 controls, ten new
independent repair controls, and the new expected allocation-defect
reproduction. All 23 separate alias-preload controls and both sealed preflights
also pass. Passing the allocation reproduction confirms R3; it does not accept
V2. The initial 26-method V2 attempt is retained in `attempt-1`; the final matrix
adds repair coverage. All V2 review tests passed. The first finalization collector
looked for a duplicated V1 source diff in V2; that path error is retained in
`finalize-attempt-1`. The collector now compares the unchanged runner against
the sealed V1 diff. No producer source was adjusted.

The ported V1 probes preserve their fault injection and actual composed targets;
only expected outcomes, packet/scratch paths, and V2's deliberate refusal of a
new normal command after a duplicate export are adapted. The original V1 probes
and sealed review remain unchanged. `fixture-adapted.py` discloses the sole
scratch-path substitution in the shared synthetic HTTP record builder.

Commands, Python version/binary hash, input/source hashes, complete output logs,
elapsed time and exit codes are retained. The final isolated preflight rehashes
all 2,332 producer input bindings. Exact runner/V9 snapshot/original six-method
block and source-delta comparisons remain intact. `protected-history.json`
rehashes all 81 V1 producer files and all 71 V1 review files against their old
seals. All 77 V2 producer files remain unchanged. Synthetic scratch is archived
with verified bytes and modes before deletion; no other project's processes or
data were addressed. No Git, compiler, simulator/frontend query, native/UI run,
screen/computer use, or physical-phone operation was performed. Physical phones
remain disconnected; all six native application cases, carrier acceptance and
GA acceptance remain pending/false.
