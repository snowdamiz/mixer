# Apple focus diagnostic runtime V1

This packet prepares exactly two XCTest methods for a later root-dispatched
diagnostic simulator attempt:

- `MixerToggleUITests/ToggleUITests/test000PublicSettingsFullKeyboardAccess`
- `MixerToggleUITests/ToggleUITests/test010EnabledFromOff`

Only `keyboard-enabled-off` and its diagnostic app are selected. The comparator
and five other application cases are omitted and receive no credit. Preparation
and host controls do not query or start a simulator. Physical phones remain
disconnected and deferred. The original V3 failure is preserved; no root cause,
focus repair, native qualification, or GA acceptance is inferred.

The packet restores the accepted compact product archive and accepted source
archive into a fresh owned `verification/apple-focus-diagnostic-runtime-v1/scratch`
directory. It verifies the archive hash and every payload byte, size, type and
mode before creating output. It also verifies the exact implied directory set
and mode, rejects duplicate or unsafe paths, and validates any declared symlink
target before materialization. It copies no old build tree. All compiled product
bytes and modes remain exactly those in the accepted product manifest.

The selected source closure derives from the immutable V3 runtime selection.
The two accepted Python diagnostic overlay sources are copied exactly. Owned
adapters relocate the native artifact module import into that closure, restrict
the app/container selection to the diagnostic app, adapt app directory inventory
to the exact compact manifest (including retained dSYM files), select the two
methods, retain session evidence, observe the exact selected test command, and
report the two-method diagnostic result. Existing installed-content, finite
permission and Mach-O checks remain in use. Unmanifested installed files fail
closed, including signature metadata if the platform introduces it. All oracle
sources remain byte-identical to V3. First acquisition Tab, the three fixed IDs,
the 12-step acquisition bound, the 12-second witness window, 8,192-byte bridge
request bound, 30/45-second per-method allowances and 600-second command ceiling
are preserved. Diagnostics cannot change a verdict or advance a failed cursor.

The command adapter matches the entire selected xcodebuild argv and allows it
exactly once. It supplies the canonical repository cwd and environment
(`os.environ` plus the original `DEVELOPER_DIR` and
`PYTHONDONTWRITEBYTECODE=1` entries), with timeout 600 and `check=False`.
Every other command uses the unchanged canonical command body. An unselected
`test-without-building` command is refused. Selected-suite console text and
result-marker presence are diagnostic observations only.
The observer is the root-accepted standalone V2 derivative, pinned by its exact
source, source-closure, receipt and root-acceptance bindings. It retains the
original nonzero `check=False` return semantics while attempting bounded cleanup
of any surviving recorded owned process group.
The integrated terminal predicate also requires the returned code to match the
observer receipt, both stream EOFs, no failed reader/cleanup, and absence of the
recorded owned process group. A surviving group fails the diagnostic slice and
retains its exact PID/PGID for narrow root recovery.

The original xctestrun file remains untouched. A mode-0600 session copy injects
only the inherited loopback bridge URL/capability variables into the two
environment maps, applies the inherited timeout/parallelization/attachment
properties, and replaces `__TESTROOT__` with the exact restored runner-products
root. The redacted derivation receipt records the original and redacted-derived
hashes and allowed changes. Cleanup retires that secret configuration after
exports. `runtime/session/session.xcresult`, command-observer logs and marker/
process/EOF timelines remain under the owned evidence root. Cleanup records each
independent operation; a failure does not prevent the others from running and
remains a failed result.

The runner creates one named `MixerFocusDiagnosticV1-<UUID>` simulator and opens
no frontend. It preserves the original runtime/device/frontend baseline checks,
shuts down and deletes only its reconciled owned simulator, and retains cleanup
evidence even after a failed test command. The CLI refuses a second runtime
directory. Native dispatch remains a separate root selection after packet
review; no native command is executed by preparing or verifying this packet.

Reproduction uses the bundled Python 3.14 runtime:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-diagnostic-runtime-v1/prepare.py prepare
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-diagnostic-runtime-v1/verify_host.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-diagnostic-runtime-v1/prepare.py verify
```

`input-lock.json` binds external inputs separately from `output-manifest.json`.
`derivations.json` identifies every changed selected source and confirms exact
compiled products and unchanged oracles. `packet.json` records the source/tree
digests, inherited revision label, selected methods and explicit unqualified
scope. `host-receipt.json` records commands, Python version, retained output,
host-control evidence and limitations. Host controls include exact archive
negatives; import with native/process/service boundaries blocked; the actual
retained strict oracle verdict and real failed cursor; diagnostic-only container
guards; exact argv/env/exit/timeout forwarding; original command-body forwarding;
owned host Python timeout/EOF/group cleanup observation; secret retirement; and
mocked full lifecycle failure cleanup. Mocked lifecycle results do not qualify a
native method. The standalone observer's host controls are separate evidence.

Full six-case keyboard, physical-phone, carrier, signing, store, immutable
published-package FieldLog, customer, operational and GA gates remain pending.
No hosted catalog-inspector or authority-driver source is imported or executed.
