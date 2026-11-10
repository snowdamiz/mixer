The existing GuestUI V1 contract blocks the unchanged real R454 EntryEditor
before a diagnostic reactor resource profile can make this slice executable.
The first unsupported operation is publishing the actual editor title field.
The unchanged `EntryEditorAppleHost.titleHost.snapshot.document` is 278 bytes,
with root kind `textField`. The canonical `GuestUIExchangeV1.finishTurn` rejects
it with `GuestUIProtocolFailureV1(phase: startup, code: document)`. No effects
intent opens and no event is admitted. Its real 308-byte note field also fails.
This is a fresh executable admission result, rather than an inference from the
known function-count rejection.

The immutable `contracts/guest-ui-event-v1.json` and canonical MixerGuest source
admit only vStack/text/button documents and activate/null events. The actual
193-byte Unicode textChange/string event fails `GuestUIEventCodecV1.decode`
with `fields`; even activate with a string fails. No public GuestUI long-note
policy exists. The native longNoteV1 policy is a different boundary. The exact
R454 100,000-byte note produces a 133,641-byte real field document and a
133,464-byte original event packet; the guest document maximum is 65,536 and
its fixed event capacity is 4,096. The latter decode fails `messageTooLarge`.
A smaller field, button-driven substitute, command-start alias, chunked private
protocol, or silently widened ABI was not used.

The existing reactor admission baseline ran first. Its independently authored
canonical `vm/tests/guest_ui/fixture.rs` module passes the actual guest-UI C
validator. The first-party CapabilityGuest interpreter executes startup, four
separate event calls and ready, then closes with zero outstanding requests,
native leases and reserved mailbox bytes. Post-close invocation is refused.
An invalid uncalled function is rejected at function 5, offset 221, confirming
that entrypoint-only validation is not substituted. This fixture is explicitly
a protocol baseline, not an EntryEditor implementation or full Swift reactor.
The canonical Swift exchange separately admits/presents/delivers a valid
button baseline and refuses stale-generation and closed-owner input.

Fresh read-only admission of the exact R327 Wasm SHA-256
`e2576db230c55688c6020116a6fc3a765b6d260c01bb87a8f43274dff9419d84`
reproduces 80,544 versus 79,966 bodies at offset 7,273. The canonical guest-UI C
validator also refuses this command artifact. Neither result is complete
validation of its bodies, execution of its reactor exports, or R454 Wasm
qualification. The accepted command profile was not executed or relabelled.

The native reference does execute the unchanged shared EntryEditor and the
unchanged real R454 Apple adapter. Both are copied from the complete ZIP whose
source-ready SHA-256 is
`15171b12ada97defb31db28ca40bd8aefb4351695bdb59f5efa5d9e32cc3d2b2`.
The fresh macOS release executable drives original routed title/note events,
SaveDraft, feature close, feature reopen and Commit as separate calls. Per-turn
observations include actual UI field bytes, model state, workspace revision,
drafts, entries and entrySaved outbox count. Exact combining Unicode, Arabic,
Japanese, emoji and CRLF survive draft save/reopen. The original exact R454
100,000-byte note survives native input and commit byte for byte, SHA-256
`9130b7d9e643c9ec1ab1940d76a55a5a47b4d28599e1a24e3d04542ae5affdef`.
Commit creates one entry and one entrySaved; duplicate submission is refused.
Old field revision and closed-host input are refused. Both feature instances
close. The port copies Workspace, calls actual EntrySaveIntent.apply, increments
revision, validates, obtains the real result and publishes the transaction.
It is an in-memory port: no filesystem durability or process restart is claimed.
The macOS adapter is exercised as compiled code; no native window/device or
pixel/UI automation acceptance is claimed.

Root coordination is required before dependent guest implementation. A versioned
editor-capable GuestUI contract must explicitly admit textField/vertical-axis
semantics, original textChange/string values and the desired text value policy.
Its encoded-document and encoded-event bounds, header event-buffer capacity,
JSON escaping/preflight limits, routing, host memory-copy constraints, immutable
contract/header identity and signed installation selection must agree. Existing
V1 bytes/defaults remain unchanged. Simply raising the reactor function ceiling
cannot fix these independently reproduced contract failures. No diagnostic
resource successor was coded because it would not unlock this ABI. After root
selects that contract, a separately isolated explicit resource profile can be
accounted across decoder/vector/ticket bounds before its dependent code is
implemented. This report does not request an unaccounted global limit increase.

Delivery is confined to this directory. `reactor-admission-harness.patch` adds
the isolated package, native admission/reference executable and owned interpreter
baseline example; product sources and VM implementation are byte unchanged.
`source/`, `source-manifest.json`, `observed-inputs.json`, `commands.json`, raw
`logs/`, `artifacts/`, `comparison.json`, `receipt.json` and `cleanup.json` retain
consumed source hashes, commands, versions, outputs and scope. No root Git or
revision lookup occurred. The initial Cargo build failed during manifest parsing
because the explicitly declared existing example had not yet been copied. One
routine harness correction supplied it; the second Cargo invocation compiled
successfully. One Swift build compiled successfully. Aggregate builds requested
four jobs each, with independent Swift/Rust work overlapping briefly. No Wasm
Swift build was attempted after the existing ABI failure was reproduced.
Two evidence-packaging bookkeeping errors were corrected without a compiler or
runtime rerun, as recorded in `scope-deviation.json`.

Scope deviation: initial filename discovery used an overly broad repository
`rg --files` traversal despite the brief. Subsequent reads were restricted.
No held file contents, process operations, cleanup or writes were performed;
held-directory traversal cannot be excluded. `scope-deviation.json` records
this instead of claiming held namespaces were untouched. All seven launched
payload/version commands returned and direct children were reaped; independent
descendant-group absence was not measured. Fresh scratch is retained, and there
were no device, remote, credential, signing or delegated-child operations.

No actual EntryEditor guest reactor was constructed or executed. Its per-event
VM/model/durable-port differential, all-body R454 Wasm validation and consuming
Swift-reactor zero-ledger close remain unverified. The native reference and
protocol-baseline close do not satisfy those missing gates. Independent slice
review is pending root. W07, W08, physical-device, immutable published-package,
release and GA completion are not claimed.
