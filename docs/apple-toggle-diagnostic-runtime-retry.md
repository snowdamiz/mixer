# Apple toggle diagnostic install-validation retry

This retry changes the handoff validator and runner only. It uses the exact
267-file handoff sealed by
`9f91c9e56d964d1c505c96ac84034b49029bf386ac1a43de5ab0eaed33eca451`,
including the same SDK26.5 comparator archive
`1c55dab124608b019ab4a1b6e0a9a2355e5f72287602b890a0a3f78aa6b30fa9`
and standalone-pan diagnostic archive
`0742f08641fdfa4fdf84dc4f69b0938fff79966348810758161d4c1be8582253`.
No app source, binary, gesture policy, selected-state behavior, or assertion in
those apps changes. This lane ran no native, CUA, physical-device, Git, or compiler
operation for the retry.

The first diagnostic session installed the comparator but failed at
`verify_restored(installedApp, ...)` with `Restored mode mismatch`, before app
launch, tests, or CUA input. Its guard incorrectly applied exact restoration
permissions to the installed bundle. The failed path and installed mode were not
recorded, so the particular normalization responsible is **unproven**. The earlier
successful preflight compared installed bytes/paths and required the main binary's
three execute bits; it did not require every installed file's mode to equal its
archive mode. This explains the validation-contract difference, not the actual
offending mode.

The failed owned device `0194AFA9-4915-493A-A7BB-75CCA5C0B973` was removed;
frontend absence and all four baseline device states were verified. Its lifecycle,
events, restored apps, selection, original validator, and original successful
preflight validator remain immutable and are bound by
`failed-attempt-analysis.json`. The frozen 267 files and historical 110-file
attempt are also reverified before the retry can start.

Root explicitly selected this finite installed-permission policy:

| Role | Permitted installed modes |
| --- | --- |
| Main executable | `0555`, `0755` |
| Two dylibs | `0444`, `0555`, `0644`, `0755` |
| Info.plist and CodeResources | `0444`, `0644` |
| Bundle root, Frameworks, _CodeSignature | `0555`, `0755` |

This permits removal of owner write permission and of dylib execute bits. The
main binary retains all read and execute bits. Dylibs are loaded mappings rather
than launched executables; this bounded validator policy does not claim an Apple
promise that installation will always choose these modes. All special permission
bits and group/world writes fail closed. Other modes, links, nonregular payloads,
missing or extra paths/directories, changed bytes/hashes, incorrect Info identity,
or changed arm64 simulator Mach-O identity also fail closed. Verification never
changes installed permissions.

Archive and restored modes remain exact: directories/main/dylibs `0755`, metadata
`0644`. Restoration explicitly reproduces them. Installed validation has a
separate entry point. It records the complete accessible path/type/mode inventory
before any assertion, including scan errors, and records the actual failed path,
mode and rule on rejection. It then checks the exact five payload hashes and
sizes, bundle/executable identity, and all three binary identities. Files are
opened without following symlinks, and identity/mode/link-count changes since the
inventory are rejected. An incomplete inventory is a failure.

Sixty host cases pass: the retained 40 archive/lifecycle/cleanup guards plus 20
permission/content cases. These cover permitted read-only and nonexecutable-dylib
modes, strict restored-mode rejection, required main execute/read bits, unsafe and
special modes, symlinks, hard links, FIFOs, extra/missing paths, changed contents,
inventory-before-assertion ordering, both exact archives, and absence of permission
repair. These are host fixtures/mocks, not native install or input receipts.

Run the read-only verifier and host checks from the repository root:

```sh
python3 -B verification/apple-toggle-diagnostic-runtime-retry/runtime.py verify
python3 -B -m unittest discover -s verification/apple-toggle-diagnostic-runtime-retry -p 'test_*.py' -v
```

After root review, use only the new runner namespace. Start its supervised cell,
retain the execution session ID, and wait for its ready message:

```sh
python3 -B verification/apple-toggle-diagnostic-runtime-retry/runtime.py session --seconds 600
```

It creates at most one owned iPhone 17 Pro/iOS26.5 (23F77) instance, named
`MixerAuthoredToggleDiagnosticsRetryRuntime`, installs the same two archives, and
starts the comparator. Root exclusively supplies actual input and screenshots
through CUA. Immediately register the exact root-started pinned frontend PID, or
explicitly record reuse of a baseline frontend. Then probe and capture each app:

```sh
python3 -B verification/apple-toggle-diagnostic-runtime-retry/runtime.py frontend register --pid ROOT_OBSERVED_PID
# If reusing a frontend that predates this session, use frontend reuse instead.
python3 -B verification/apple-toggle-diagnostic-runtime-retry/runtime.py probe self-tests
python3 -B verification/apple-toggle-diagnostic-runtime-retry/runtime.py capture comparator-programmatic
python3 -B verification/apple-toggle-diagnostic-runtime-retry/runtime.py launch diagnostic
python3 -B verification/apple-toggle-diagnostic-runtime-retry/runtime.py probe self-tests
python3 -B verification/apple-toggle-diagnostic-runtime-retry/runtime.py capture diagnostic-programmatic
```

`probe` retains false checks with `checksPassed: false`; collection success is not
a test pass. Strict `command self-tests` still requires 12 comparator or 19
diagnostic checks. All touch/AX/key/paint/scroll qualifications from the original
handoff remain required. Derive current coordinates from CUA and retain exact
actions. Use the standalone pan reference and an upward list drag as independent
positive controls before attributing missing authored-pan behavior.

Finish on every outcome and wait for the supervisor's terminal cleanup result:

```sh
python3 -B verification/apple-toggle-diagnostic-runtime-retry/runtime.py finish
python3 -B verification/apple-toggle-diagnostic-runtime-retry/runtime.py status
```

The reused supervisor cleans up on finish, its bounded deadline, interruption,
installation failure, or command error. It validates device identity, preserves
all baseline devices/processes, signals only a registered unchanged frontend,
and polls transient post-SIGTERM states without signalling again. After the
supervisor exits, `runtime.py cleanup` safely retries an incomplete cleanup.
Hard process destruction or host failure still requires that recovery command.
New native installation/input evidence, carrier acceptance, production adapter,
physical phones/VoiceOver, external FieldLog, stores, operations, and GA remain
pending.
