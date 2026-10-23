# Independent private durable I/O review

No actionable finding. The review binds the owner's 139-source frozen export and
manifest `d27e35c2f6897c72384ccd566b5268f8b8a6d1d96e0b5d57d6b4bb96aefb26ff`.
The new private directory implementation, C shim, package target and seven tests
were inspected against unchanged legacy durable I/O. All 139 export hashes and the
five new/changed live source hashes were checked during the independent probe.

The new primitive preserves held directory/lock descriptors, regular-file and
single-link checks, nofollow opens, fd-relative mutations, exclusive temporaries,
write/fsync/rename/directory-sync ordering, EINTR retries and idempotent close.
The explicit read, payload, chunk and state ceilings precede mutation. Errors do
not promise rollback of an actual write/rename; the future store actor must poison
uncertain operations and retain ownership, as the approved architecture requires.
All accesses, including construction and close, must be serialized by that actor;
this private `@unchecked Sendable` primitive is not itself a concurrent store.

Pruning opens a fresh directory stream relative to the held descriptor. It retains
at most 1024 bounded names and validates the complete bounded inventory before
deletion. It does not allocate a FileManager listing or enumerate a replaced path.
Only exact digest payload/part names and UUID state temporaries are removed, while
keep-set names, the lock and unrelated data remain. New source and C symbols are
separate from the legacy implementation, which remains byte-exact to 1ab4d4ee.

An original review-only `@testable` command-line consumer links the owner's
existing unchanged Debug static library/module, avoiding a duplicate SwiftPM graph.
It passed 29 checks: the exact 1024-entry boundary; 1025 refusal before deletion;
fresh listing and keep-set behavior; state/read/append/size/publish/remove/prune
after original directory rename and symlink replacement; outside target retention;
symlink, hardlink and FIFO lock refusal; FIFO append refusal; and closed-operation
mutation rejection. The entire probe runs in a 20-second subprocess timeout because
FIFO open semantics are platform-dependent. Prompt rejection is observed only on
this Darwin host. A non-`@testable` negative compile confirms the directory type
is unavailable through public import.

The owner seven I/O plus sixteen material tests passed debug, release and Swift
TSan. Their exact log bindings and 23-case counts were audited and reused. Official
iOS and Android module/object compile receipts and artifact hashes were likewise
checked; there is no physical/mobile execution claim. C shim bytes differ from
the old shim only in the header and function names. Old Swift I/O, old C shim and
old header match their historical Git blobs exactly.

`run.py` records exact immutable input/library/probe hashes, commands, compiler
version, outputs and scope. `finalize.py` seals review source/evidence without
build caches. The probe's initial authoring compile required explicit MainActor
annotations on its own top-level counter helpers under Swift 6; this changed only
the review harness before its recorded run, not production code. All filesystem
work is within fresh disposable command-line test directories.

This slice adds no updater, coordinator, verifier authority, adapter/session
construction, actual lifecycle retirement or production operation. Source review
and internal testing are not OTA authorization, installed graph attestation,
actual health, package publication, signing/store or GA evidence. No device was
queried or run, and this lane made no production edits or commits.
