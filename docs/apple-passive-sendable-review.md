# Passive lifecycle Sendable correction review

The minimal copied observer correction and its one successful generic build are
accepted for this development prerequisite. There are no blocking findings. This
review binds producer handoff
`207821bc258c351b1767932ad7b2e85dd7f621f3ad7e56054bcb3cfdcf87ed88`
and its 81 members. Root separately selects any runtime preparation or execution.

Only the optional String identity and the Sendable notification kind cross the
synchronous `MainActor.assumeIsolated` boundary. `withExtendedLifetime(object)`
encloses the entire actor call, so the actual notification object remains alive
while its address is compared. Another live object cannot reuse that address;
the identity is neither queued nor accepted after the lifetime ends. Strong
local upgrades of the weak application/window and current scene provide the
other comparison operands. The successful match supplies that actual owned
object to the unchanged snapshot capture. Nil and foreign identities fail closed.
The address is diagnostic identity only, never release or input authority.

The main-thread guard still runs before identity projection. Off-main delivery
only increments the existing locked fault counter. The correction adds no
unsafe conformance, actor annotation, task, async hop, or timer. The existing
`@unchecked Sendable` fault holder is unchanged and its access remains locked.
The fourteen subscriptions, weak observer/window ownership, current-scene
selection, sequential reads, snapshot schema, bounds, oracle and input are
preserved. The already documented conservative filtering and non-continuous
coverage limitations still apply.

The reviewer independently regenerated the unified diff from both archives and
matched it byte exactly to the root-selected failed-build proposal. The
candidate archive is
`bf31888a14490e83e2424f458eac0cf8f56258d581ff2fc4034840b0d1783663`.
Only the observer differs from its 42-member producer archive; the other 41
members and 39 unchanged earlier-baseline members match in bytes and mode. The
closure retains 37 Swift files, including 12 Prototype and four harness files.
The original failed-build seal and all of its evidence remain intact.

Nineteen fresh independent boundary checks passed on each exact archived adapter:
the correction in Swift 6 and original in Swift 5. Results match. These narrow
macOS controls use real synchronous NotificationCenter delivery with the
explicitly labeled public-surface UIKit double. They exercise nil and bridged
foreign objects in each family, nested current-scene replacement, nonnil
off-main delivery, ended weak ownership, and synchronous object lifetime and
release. The producer's same 88 semantic checks and 116/371 unchanged Foundation
checks were inspected and their sealed command/output bindings verified; the
historical suites were not rerun by this reviewer. Lifetime controls observe
liveness during the callback, but the no-address-reuse conclusion also depends
on the reviewed explicit lifetime enclosure; allocator stress is not proof.

The retained generic recipe matches the failed attempt after substitution of
only its owned scratch prefix. Eight commands exited zero, with EOF, no signals
or timeouts, and absent owned process groups. The exact selected source archive
matches the built source archive after removal of the outer `accepted/` prefix.
The 55 fresh product members bind to archive
`495f83c4702f7b229be495756f0a524c700f07159c5e21975dea471d118a8904`:
13 app and 42 runner files. Independent in-memory Mach-O parsing confirms the
four compiled targets are arm64 iOS Simulator, minimum 26.0, SDK 26.5. The product
Info.plist retains the previously reviewed minimum-OS derivation. The 21 warning
occurrences match the full original qualification message multisets. No generic
or native build was rerun for this review.

Exact source/archive/tree digests identify the tested inputs. The producer's
current correction context reported by root is `7b6048642b42e4900cccff4e14aa0fe8949ab35e`;
the inherited `6b8aba` fields in producer and review finite receipts denote the
historical accepted-input context. `delivery-context.json` records the distinction.
This reviewer ran no Git commands. All producer, prior-review and failed-build
handoff members were rechecked after the final producer seal.

All owned review scratch was removed after process-group, EOF, single-link,
stable-inode and empty holder checks. Producer cleanup was also verified from
sealed receipts and scratch absence. Native instances and other projects were
untouched. No simulator/device discovery, UIKit runtime, screenshot, or physical
phone run occurred. Historical Settings Passed / first Tab Failed remains
unchanged. Runtime ingestion, original oracle success, full UI, physical-phone,
FieldLog published-consumer, signing, store, operational and GA acceptance remain
pending. Root approval of a separate runtime packet is still required.

The review verifier only reads files and archive members in memory. Pass the
exact review handoff digest from `handoff.sha256`:

```sh
python3 -B verification/apple-passive-sendable-review/verify.py REVIEW_HANDOFF_SHA256
```
