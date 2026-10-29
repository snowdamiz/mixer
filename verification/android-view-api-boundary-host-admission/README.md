# Focused Android view API hosted admission preparation

This is a concrete runner/admission candidate, held for independent review and
root selection. It has not been executed or dispatched. `workflow.DRAFT.yml`
is outside `.github/workflows`; it is not installed. No compiler, JVM, SDK/D8,
product, Node oracle, Rust/Swift/Elixir, native/UI/capture or phone runtime ran.

## Frozen source scope

`input-manifest.json` binds all 115 producer members, its manifest/freeze, the
root source-selection contract, independent source-review packet, frozen inspector,
Linux tool profile and SDK/image observations: 148
explicit file identities. Producer freeze SHA256 is
`c458497920a6cf454433f2f96bbcdf42fbf8b6945e55e5a76c813dddb00af8ff`;
manifest `e52dd5bd9c415a68c843724a24fec03c72c64dbce7fae2d18377c646a4b35834`;
product16 tree `d767f19554c88bd24f58663de268d7a80119522380cfeb4043c37d35b432a21e`.
Independent source-design seal is
`f4c171e31f393750a39fbb10ba53d7d63f78174630a7f46f362680d41a6e2cac`.

The host compiler receives only the sixteen frozen product sources, 86 frozen
mechanical Android/JNI leaves and `ViewApiBoundaryTests.java`: exactly 103 Java
files. It then runs only `dev.mixer.android.ViewApiBoundaryTests` with the frozen
9,587-byte descriptor. Its thirteen groups contain 152 finite interruption
invocations and use actual OwnerLifecycleV2-issued operation tokens. This does
not start NativeOwner, register observers, drain product startup queues, load
Unit A or run the historical matrix. Direct view-component coverage does not
admit full V2 rendering below 36.

The separate official SDK37 compile receives only product16 plus
`tests/cross-leaf/NativeBridge.java`: exactly 17 Java sources. It receives no
mechanical host leaf or test source. Pinned D8 then consumes exactly the newly
inspected SDK class map, with `--min-api 28 --lib <pinned android.jar>`. D8 is
invoked through the exact Java executable and d8.jar entry point rather than a
shell launcher. This is unsigned compilation/reference evidence only.

Both compiles use `--release 17 -proc:none -Xlint:all -Werror`, an explicit empty
sourcepath and the appropriate empty-host or official-SDK classpath. No implicit
source discovery, argument-file discovery, provider installer or fallback exists.

## Future bounded command plan and custody

`collect.py` constructs six fixed commands plus one exact emitted-map D8 command:
Java version, javac version, D8 version, host compile, focused main, SDK37 compile
and D8 min28. Each command has explicit argv and an allowlisted environment.
No extra test, discovery invocation or retry is selected. Version output is
checked against exact selected expected stdout/stderr bytes; names alone do not
identify the toolchain.

Each owned child has60 seconds active wall time, 60 CPU seconds, 8 GiB address space,
4 MiB per output stream and64 MiB per file. JVM heap/metaspace/code-cache reservations
are finite. Cleanup has a 6-second loop plus at most a 2-second direct-child wait.
These numeric limits are finite hypotheses, not prior successful measurements.
Unsupported limit/session/wait facilities or failed commands refuse; they do not
trigger a fallback. Scratch is bounded to 1,024 ordinary files / 128 MiB and retained
on success or failure. No old process or scratch cleanup is attempted or claimed.
The selected standalone collector has 2 GiB soft / 8 GiB hard address space, 256 MiB per
file and 900 CPU seconds; children raise their soft address limit only within that
reviewed 8 GiB hard ceiling. Source/tool hashing and inspection occur outside each
child's 60-second active deadline and within the separate 15-minute collection step.
The 22-minute job reserves checkout 2, data setup 1, collection 15, upload 2 and scheduling 2
minutes. Provider cancellation, host loss or outer timeout may prevent terminal
custody or artifact preservation; an absent/incomplete receipt remains held.

`custody.py` installs limits only inside the new child. It starts one new session
and retains the direct leader unreaped with `waitid(WNOWAIT)` while any numeric
group signal authority remains. It drains stdout and stderr separately to actual
EOF, preserving the two observations independently. On bounded failure, only that
still-pinned group can receive SIGTERM/SIGKILL. Signal authority is permanently
retired before direct reap. Providers without required waitid/WNOWAIT interfaces
refuse before spawn; there is no poll/reap fallback.

Root explicitly selected one terminal `killpg(pgid,0)` observation after reap.
ESRCH means numeric group absence at that instant. Success or EPERM is held:
there are no later signals, retries, probes or cleanup claims. This observation
does not prove permanent process identity, escaped-descendant absence or provider
disposal. Direct exit observation, permanent signal retirement, direct reap,
terminal group absence, stdout EOF and stderr EOF are distinct acceptance fields.

Every command rechecks frozen source, the admission seal, copied source against
the original manifest, inspector identity, installed workflow identity and
official tool distributions before and after execution. The original inspected
host map remains pinned through the focused JVM command; the original inspected
SDK map remains pinned through D8. Refusals and setup failures remain under the
attempt's unique output path with argv, environment, source/tool identities,
independent streams and custody state. The collector does not delete scratch.

## Independent emitted inspection

The separately owned `inspect_artifacts.py` reads actual ClassFile and DEX bytes.
The collector calls `inspect_classes` for both emitted roots, with the exact
pinned official android.jar as hierarchy data, and calls `inspect_dex` for the
single emitted classes.dex. Each report must explicitly return accepted=true.
Its final file and seal identities are bound before this packet can freeze.

Inspection covers the three emitted API helpers, native symbolic owner/name/
descriptor references, actual SDK_INT guard branches, setter order, original
Mutation postchecks, constructor shape and DEX invocation/register references.
The exact class evidence resolves inherited NativeField→EditText→TextView setter
declarations from official SDK bytes. DEX and class evidence are paired; neither
claims Android linkage, ART verification or native runtime behavior. Source
matching and output text alone never replace emitted inspection.

## Selection and provider boundaries

`tool-profile.json` selects a concrete Ubuntu 24.04 / Linux x64 expected-file
profile. The current successful hosted owner receipts identify Temurin 17.0.21+9
launchers. An official, checksum-verified archive matches both launcher hashes
and supplies 74 exact runtime file identities (198,674,633 bytes), including
release, modules, ct.sym, native libraries and configuration. Before every child,
the actual installed ordinary files and closed conf/lib membership must match.
The manifest excludes only lib/src.zip and the provider CA trust path. The source
link, docs, legal files, other executables and jmods are outside selected lookup
scope. No installed runtime library scan occurred during this preparation.

The exact platform and D8 jar identities come from accepted SDK37 evidence.
Official published Ubuntu image inventory supplies the fixed SDK paths. The
published inventory version 20261026.354.1 is distinct from the earlier successful
VM job's 20261025.353.1 image; neither proves availability in a future run. Sample
platform class major 52 and D8 main major 55 remove one known JDK17 obstacle;
complete compatibility and execution remain pending. Missing or different bytes
refuse before any Java child. `tool-profile-historical-macos.json` preserves the
old Mac identity as provenance only; the collector cannot select that mode.

Root explicitly admits the Ubuntu Python/bootstrap/stdlib, operating system,
dynamic loader/system libraries, CA trust and GitHub action infrastructure as
provider boundaries. The collector starts through `/usr/bin/python3 -I -B`,
requires the known 3.12.3 provider version and records its resolved executable
hash and sys.version before any Java child. An already-running collector cannot
independently prove its own bootstrap. No hermetic system-library or provider
disposal claim is made. There is no setup action, download, package-manager
invocation or installer. A different product tool identity needs a new reviewed
profile; no automatic first-observed identity is accepted.

The runner requires an external root selection binding its seal, runner/custody,
inspector, frozen source and exact installed workflow hashes plus an immutable
GitHub source revision. It requires the selected repository and first run attempt.
Root supplies a fresh 64-hex dispatch nonce. GitHub assigns the numeric run ID after
dispatch; the collector records the observed ID and nonce. The collector alone
does not enforce nonce uniqueness across separate fresh workflow runs. Root's
delivery helper must consume the single operational allowance before dispatch,
never repeat an unknown outcome, and reject duplicate/unmatched dispatches.

The manual workflow draft materializes root JSON as data, runs only this collector
and preserves evidence with always-upload. It contains no GitHub dispatch code.
Checkout and upload use exact official action commit identities already present
in the reviewed identity-network workflow; `workflow-actions.json` records the
source evidence. Their GitHub provider/Node infrastructure is an explicit
external boundary, outside the seven custody-owned Java-tool children.
Root owns actual workflow installation, Git/delivery, tool/profile selection and
any future run. This packet supplies no local or hosted runtime authority.

## Preparation evidence and limitations

`test_preparation.py` installs denied real process/session/group/signal/timer/wait/
socket surfaces before importing the candidate collector or custody helper. It
uses only filesystem/JSON/AST checks and synthetic process/stream/clock behavior.
Its mock controls test separate EOF/reap/group fields, lost/retired authority,
post-reap group existence/EPERM, no later signals/probes, validation/setup failure
preservation and exact source/compiler closures. The original failed source-path
lookups and every control attempt remain in ignored `local/`; no subject runtime
setup was attempted. Runtime or compiler success cannot be inferred from these
prepared tests.

All protected hosted/store/.wrangler files, old local held PGIDs, FieldLog's old
run/process custody, other projects' processes and the canonical VM slice remain
outside this lane. No such process was accessed, queried, signaled or cleaned up.
The held v5 launcher, equivalent startup experiment, complete matrix, Unit A and
189-disposition/280-subject evidence remain held. New source-pair reconciliation,
SDK-axis selection, public V2, lower-API full rendering, native/IME/TalkBack/OEM
parity, physical phones, OTA/release/publication and GA remain pending.
