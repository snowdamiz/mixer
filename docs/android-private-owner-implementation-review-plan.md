# Independent private Android owner implementation review

This is the sealed preaccess design for the independent implementation lane. It
accepts no candidate: the implementation is changing and has not been read. Root
must admit an immutable candidate before this lane reads its product source,
tests, ConcreteHostLeaves, probe, implementation documentation or evidence.

The binding product remains `mixer-product-plan.md`. This lane owns this document
and `verification/android-private-owner-independent-review/**` only. It does not
edit product/profile/CI/root metadata, predecessor packets, indexes or another
lane's files, and does not commit or push. No dependency is added. Host-only work
does not qualify Android framework/JNI behavior, public V2, OTA or GA. Native
runtime, simulator/emulator, phone, UI and capture work remain paused. No process
discovery is permitted. Frozen hosted inspector, authority driver, Worker V2 and
callback harness lanes remain inaccessible.

The exact design packet is `verification/android-private-owner-independent-review/preaccess/`.
Its custody map records all inputs, tool identities and baseline source digests.
It uses the four selected contract documents, the amended roster and root
implementation selection with SHA-256
`d698ad2ca8ed0706038a652a5b665bb8818fdc4388ffaf34194a73bec11ab6aa`.
That selection binds seven packets, 303 unique members and 5,595,445 bytes. Source
inspection uses only `git show 0b8e3fd8bdd86902f7d9d28e0cba01bcdbb5ce1c:<path>`
snapshots. A current checkout file is never substituted for that baseline.

## Admission and independence

Before candidate access, seal this plan, independently authored case families,
all 1,288 baseline V2 site/case rows, five V1 controls, source/input map and
commands. The design checker establishes completeness/custody only. It executes
no candidate and must not be reported as product validation.

Root admission must identify the candidate revision or exact tree, every source
path and SHA-256, producer test/runner/leaf/probe hashes, source-profile proposal
and pending limitations. Candidate bytes are copied once into a new review-owned
candidate directory and independently hashed. Review works from that admitted
snapshot. Any repair receives a new candidate/addendum; the sealed preaccess
packet is never rewritten. A root message permitting access is required in
addition to a producer readiness claim.

Independent tests are authored against actual bodies. Closure A compiles the
ten exact production sources in its admitted roster, including actual owner,
unchanged core, coordinator and observer; its renderer leaf is orchestration
instrumentation only. Closure B compiles and executes all fourteen exact product
subjects, including actual NativeRenderer, Gate, Input, Record, control subclasses
and helpers. Compilation, class loading and scripted renderer flags are never
counted as concrete behavior. No product copy, overlay, reduction, translation or
replacement is allowed. Actual standard-library classes remain real.

The 73 Closure B Android/JNI leaf sources may be reused only after this reviewer
independently audits their exact admitted bytes as mechanical leaves and root
admits that reuse. Until then they are unread and untrusted. The audit checks all
73 FQCN/path identities, nested owning-file identities, imports and executable
bodies. Leaves may expose primitive platform facts, mutable text/parent/layout
state, call counts and controlled synchronous callbacks. They cannot manufacture
core tokens, installed/environment/current authority, successful validation or
product gate state; they cannot execute hidden product logic or expected decision
logs. NativeBridge may return independently authored raw packet bytes and opaque
JNI tokens and count calls; it proves no Swift/JNI execution. The test driver,
not a leaf, selects fault timing and inspects actual product state. If a reused
leaf fails audit, stop its use and request a bounded roster repair/admission.

## Call-site coverage and observations

The amended contract has exactly 184 mandatory baseline V2 barriers and five
separate unchanged V1 positive baselines. Every V2 barrier receives `clean`,
`terminal-at-entry`, `terminal-before-return`, `dirty-at-entry`,
`dirty-before-return`, `ordinary-throw-after-callback` and
`fatal-throw-after-callback`. Every newly introduced callback-capable call in
the selected regions receives an additional ID and the same seven cases. A moved
baseline site retains its historical ID with an explicit candidate binding. No
unreached or replaced site silently disappears. A failure is retained; no missing
site becomes a pass through a family-level aggregate.

The sealed input map retains exact source/line/column/expression anchors, complete
baseline source digest and byte offsets. It distinguishes all same-line sites,
including repeated expressions. After admission, bind each site to actual class,
method descriptor and invocation bytecode offset, plus candidate line/column and
the exact enclosing body. Use independent `javap -c -p -l -s` inspection to bind
the source expression to the invocation; source-text matching is supplemental.
At a leaf hook, JDK StackWalker frame descriptor and bytecode index identify the
reached production call. Distinct same-line invocation offsets must stay distinct.
If instrumentation cannot identify a site unambiguously, that row is pending.
No broad method-name hook or `faultV2()` control substitutes for call-site proof.

For each injection, record before/after shared terminal, draw/input and operation/
presentation identities; actual current/pending Gate.open flags; reached site;
callback phase; cancellation/report claims; call deltas; and actual owner/core/
coordinator/observer ledger outcomes. Record flags at callback entry before the
callback's first action and after its seal action. An initially live callback may
start open; the terminal/dirty entry itself must close authority before its next
callback-capable effect. A transaction starts with live gates closed. Do not claim
a pending Gate exists before actual publication. Prove that terminal/fatal reentry
blocks the next forbidden Mixer mutation, commit or event and that no old scope
recaptures a new token. Necessary independent cleanup has its separate bounded
scope; it must not bind/layout, send input, reopen authority or start operations.

## Reviewed clarification: dirty captures and completed input results

The additional root-proposed contract input is
`docs/android-private-owner-dirty-transaction-disposition.md`, SHA-256
`2a1574cea4d94b21bbf5d59b64484700ca7dcdf8d94fd3822fdf8fb63c5f0fa4`,
5,574 bytes. Independent opinion: acceptable as a mandatory clarification, with
no further wording correction required. The earlier 5,343-byte draft and the
reviewer's later forwarding-versus-refusal correction are retained separately in
the packet; the revised document resolves that correction. This is source-contract review,
not implementation acceptance; root must select the clarification.

Baseline Observer.invalidate advances generation before notification;
NativeEnvironment.current rejects a generation mismatch and rereads the concrete
tuple; coordinator transaction/refresh paths validate that capture; unchanged
core.complete retires a matching failed or uncommitted operation. Thus lifecycle
dirty with a still-current capture may finish, complete successfully, keep gates
closed and schedule one drain. Actual observer invalidation after capture but
before a remaining concrete validation must fail that validation and retire via
the real operation-failure path. It cannot forge success, refresh/retry its
captured operation or weaken generation checks. Before-capture invalidation may
be incorporated into the later fresh capture. Outside an operation, ordinary
presentation mismatch seals and invalidates through the same observer so a fresh
drain can capture; it is not itself a renderer-terminal reason.

The exact timing matters: do not infer that every after-capture notification is
followed by another concrete validation. In particular, do not add a callback or
capture to the successful commit/finish interval. Admit explicit cases before
capture, after capture, in attachment/layout, before commit, in refresh and input,
and at any admitted JNI callback seam. Preserve all seven cases/site; distinguish
lifecycle-only dirty and actual observer generation-changing stimuli in each
receipt. This clarification does not qualify seamless stale-transaction recovery.

A real IME delegate may synchronously change Editable, invoke the actual
TextWatcher, dispatch through the actual owner and commit successor P1 before its
P0-scoped call returns. P0 remains immutable. A scalar/reference postcheck may
permit an immediate return of the completed result only when its sole mismatch
is that clean live successor. That branch performs no capture, connection/native
call, event, mutation, new token adoption or other continuation. Dirty/terminal
closure rejects; an observed Error remains fatal. Every additional forwarding
call validates the captured scope before entering its delegate; each later wrapper
invocation captures its own valid scope and retains concrete record/focus checks.
Test every forwarding family with actual synchronous successor execution; test
nonforwarding overrides with explicit refusal and zero-forward controls. Both
families retain exact-current, dirty, terminal and stale controls; fatal behavior
is exercised wherever a selected call is reachable. No site or seven-case row is
removed. A canned delegate result alone cannot establish the positive synchronous
sequence. Bytecode review supplements it.

## Fault families and independent oracles

`cases.json` is the exact independently authored test design. It defines setup,
stimulus, required observations, forbidden effects, positive controls and scope.
Its families cover inert allocation; main-before-stale checks; observer publication,
readiness, eight-slot registration/removal and once binding; exact operation and
presentation ownership; early virtual constructors; every barrier; immutable
transaction/live/cleanup scopes; null-operation positive scrolling/input; all IME
families; serial exhaustion and stable bounded cancellation; clearTouch's three
independent attempts; recursive claims; first primary/first fatal priority; exact
typed single renderer reporting; all six renderer causes; single-slot terminal
tail/disposal; stale/cancelled deliveries; never-returned active work; scalar-only
commit/finish; exact retained-packet refresh; synchronous unbuffered input; core
allocation/completion failures; rollback; actual decoder witnesses; unchanged V1;
and source/profile identity boundaries.

Independent fault values are distinct identity objects: ordinary primary A,
ordinary cleanup B and fatal Error E. Oracles compare identity, actual attempts
and effects rather than exception messages or expected decision traces. Numeric
exhaustion uses admitted package-private seeds or review reflection into counters
only; tests never mint or replace authority tokens. Queues model Handler.post as
non-inline. A blocked operation uses a bounded test latch; the reviewer asserts
pending disposition before releasing it in finally. It does not leave a host
thread or child running to demonstrate pending work.

Independent packet witnesses begin with the sealed literal packet fixture and
derive successors by explicit identity-preserving revisions, replacements and
malformed variants. The descriptor fixture must be independently authored from
the frozen decoder grammar, with distinct provenance and exact byte digest in
the candidate test addendum. Assets supply bytes through actual
InstalledAppearanceV2.capture; actual UiPacket/Json/AppearanceDescriptorV2 decoders,
resolver, geometry, path and authored-toggle bodies execute. No leaf constructs a
trusted capture. Negative decoder inputs must fail before native mutation; a
real positive packet must reach actual view construction/layout and input.

## Runner and acceptance boundaries

The exact executable commands authorized now are in `commands.json`: generate
the design, run its structural/custody checker, seal and verify. Future candidate
Java source lists and test bindings cannot be selected before root admits exact
bytes. Materialize them as a separately sealed candidate addendum and record
literal argv before executing. Its expected command templates are fixed in the
preaccess commands file; replacing a placeholder is binding, not permission to
change scope or expected behavior.

Use official JDK 17-target compilation with `--release 17 -g -Xlint:all -Werror
-proc:none`, explicit source files and empty source/class paths; remove implicit
JVM environment options. One owned child at a time, 120-second wall timeout,
256-MiB Java heap and 2-MiB stdout/stderr caps per command. Kill/reap only the
owned child group on timeout/cap failure. Retain exact argv/environment/tool
versions, source/tree digests, streams, exit status and reached-site results,
including failures. Scratch is exclusive and review-owned; remove transient
classes/scratch after either success or failure and record cleanup. Preserve
inputs, logs and other projects' files/processes. No network/install or external
dependency is needed for this preaccess slice.

Source/bytecode review of commitV2 success through finishV2 follows the exact
reachable body, including invoked helpers: only direct scalar/reference checks,
prepared swaps and the existing branch/direct call belong there. No capture,
native mutation, callback, allocation, core call, predicate, report or cleanup is
permitted. Deferred failure reporting occurs after commitFinish clears. Counted
JNI leaves alone cannot prove this property.

After candidate admission, verify exact core relocation SHA-256
`4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6`, one
canonical exported core, unchanged public V1 routing/padding, all 22 SDK sources
and default descriptor/wire identities. Profile `mixer.android-source-pair.3` is
selected as an ID only. Exact source-map hashes require root selection before
CLI/common/driver/copied-consumer qualification; this lane must not infer them or
run consumers early. Official SDK Java/D8 and app-owned Swift/JNI cross-builds,
prior accepted host regressions and exact-source consumer qualification remain
additional gates. This preaccess packet executes none of them.

Stop after sealing this plan and report its checksum to root. Remain stopped
until root admits the candidate and any required mechanical-leaf reuse. Later
host results remain private development evidence. Device/accessibility/performance,
separate-repository immutable published FieldLog, signing/store, operational and
accountable GA acceptance remain pending.
