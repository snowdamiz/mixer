# Affine refusal and strict synthetic-session correction

This is a corrected **Python host model and interface sketch**, awaiting fresh
independent review and root acceptance. It supplies no product/native/Rust
implementation, compiler receipt, policy, root funding or operational grant.
Only this new packet was written; all earlier packets, failures and returns
remain byte-for-byte unchanged.

The binding C1–C2 contract is
`b023b8e816c5a68cfe565f0cf901676998ec50b189aca1ead0bb49dbce142d51`.
Its returned candidate seal is
`f3e4ac2543fde4fe7b1e03019fb49bbb5ba9aca078097e5aeb0fc972703de7a3`
(61 members, 1323422 bytes); the review seal is
`a64f0cbb775265509b98bea63faca5e144e6d4b8f685898251ea12d506c8840a`
(34 members, 829896 bytes). Root's return is
`97aa4d370d6c490e37302ad036e2af029cb6607972147c40c7dd63c410a28c9c`.

`model.py` now prepays one fixed correlation-ingress program **before admission
is published**. Twelve synthetic operation units and twelve synthetic storage
units come from the existing reservation, whose cleanup provision remains
separate. These units model a fixed program: attempt, carrier, four File slots,
four body slots, original-error slot and replay-refusal slot. They select no
native prices, allocations, compiler layouts or resource quantities. A refused
prepayment cannot publish a view. The ticket is funded once, and generation
replacement cannot renew it.

The first live admitted call consumes the attempt and retains the supplied
carrier before any fallible forbidden-expected, view, selected shape, File or
buffer check can reject it. Capture examines at most four slots in each exact
built-in tuple/list. Safe Files must be live, valid, uncontrolled and unadopted,
with a valid regular full identity; capture immediately places them in the same
paid outcome. A distinct fixed roster records registered paid bodies. Unknown
collections are never enumerated. Invalid/raw/already-controlled/foreign Files
are never adopted, closed or stolen. Paid buffer registration is checked by an
exact private allocation record, without walking an arbitrary supplied carrier.

Four Files with only three paid initialized buffers therefore refuse **after**
all safely represented owners are retained. They may retire completely before
release. Wrong types, unknown/oversized collections, unsafe or foreign ownership
instead set a sticky unresolved obligation. Destruction may retire the known
safe roster, but never claims complete retirement or releases any of the whole
storage charge while that obligation remains. The selected result and original
refusal remain live in that incomplete outcome. Retirement uses only the safe
captured roster, never the unchecked public File/body collections.

Every first refusal preserves the same original `Refused` object. Removing the
forbidden fourth argument cannot make a retry succeed. A replay has one finite
prepaid refusal slot and retains the first later carrier reference. It performs
no new collection walk, ownership conversion or close attempt. A different later
carrier sets permanent unresolved retention; further caller objects and their
creation, argument/exception-frame work and backing remain **external caller-side
obligations**. This deliberately grants no unbounded public retry handling or
whole-host resource closure. Repeated raises reuse the original refusal (or the
prepaid replay refusal following success), without adding diagnostic owners or
minting tickets. Calls before a published admission or after retirement remain
external misuse; they cannot establish a new attempt or resurrect retired owners.

Complete ordinary distinct-handle retirement still requires exactly **47**
cleanup units. Capture metadata uses the existing diagnostics/results/carrier
retirement places: both error slots clear with diagnostics, retained carrier
references clear with results, then the carrier retires. A 46-unit provision,
any failure/unwind, raw obligation or unresolved ownership cannot release.
No native healthy-close claim is made. The original allocation requested/slack/
failure-backing contract, conservative raw-slot retention and separately funded
one-shot cleanup protocol remain.

The synthetic JSON decoder now checks exact top-level and nested object keys,
primitive types and domains **before equality or expected construction**:

- Four digests and nonce are exact 64-hex strings; all five validation limits
  are positive exact u64 integers.
- Extent is a positive exact u64 integer. Identity contains exactly device,
  inode, length, mode, mtime, mtime_ns, ctime and ctime_ns.
- Device/inode/length/mode are unsigned u64; all four timestamp fields are signed
  i64. Floats and bools are rejected everywhere. Mode must identify a regular file.

The fully typed decoded source identity and extent must then equal the acquired
source owner. Expected correspondence uses those decoded values, so malformed
records cannot be normalized into acquired typed values by Python equality.
Negative signed timestamps, including signed-boundary values, remain valid.
The three retained float witnesses now fail before admission, as do adjacent
bool/non-integer, key, range and regular-file violations. This remains a synthetic
record parser under the trusted quiescent local-launch premise. It authenticates
no real manifest, image, native bridge, product parser or hostile launcher.

The minimum existing setup/loader opens followed by private complete correlation
before leaf remain the selected *direction*. All existing loader checks remain
required, and distinct handles for the same immutable objects remain positive.
Same-handle loading remains an optional, larger unselected route.

The exact final bounded command is:

```text
/usr/bin/env -i PATH=/opt/homebrew/bin:/usr/bin:/bin LANG=C LC_ALL=C TZ=UTC PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 /opt/homebrew/bin/python3 -B verification/swift-guarded-snapshot-prepaid-input-owner-affine-refusal/run_bounded.py all-final all
```

It passes **110 methods**, with zero failures: all 76 prior candidate methods,
all 11 recent independent-review methods rebound only to this candidate, and
23 newly authored C1–C2/adjacent controls. Reused review methods are regression
evidence, **not fresh independent review**. The final exact sources are frozen
in `commands/all-final`, with source tree SHA256
`611489b3d9a7664eb412f04bdc8af031a9623e72eb18fc16e22f5e436ec59d5b`.

Retained controls cover all 13 adoption refusals and conservative raw retention,
39 acquisition exhaustion positions, **100842** bounded read schedules, all
47 retirement failures and 47 unwinds, cleanup 46/47, nine provenance groups,
32 full-identity field substitutions, distinct handles, owner/view/generation/
refund controls, noncircular bootstrap and allocation slack/original-error
envelopes. New controls cover the four-Files/three-buffers witness, old API,
selected type/count/collection, duplicate/invalid/foreign/raw/dead handles,
buffer count/registration/initialization/sharing, copied/foreign views, exhausted
operation/storage budgets, finite replay with no collection walk, strict nested
schema and valid negative signed timestamp/full-identity dispatch.

`focused-attempt1` passed 26 methods. `all-attempt1` passed 109 after clearing
fixed error/carrier slots at retirement; source review then added the first-call
unknown-collection control. `all-final` passes the final 110. Every command keeps
its exact source snapshots, complete minimal child and actual parent environment,
explicit argv/cwd, Python version/executable hash, source revision from the frozen
root return, output hashes, exit/time and before/after **479 frozen input paths**.
All inputs stayed unchanged. All three children were reaped and their exact
owned process groups confirmed absent, with 55-second deadlines and no scratch.
No old runner, one-shot seal or broad/native harness was executed.

Initial source copying, navigation and editing are preparation only. A first
patch failed because copies inherited frozen source permissions; only the new
copies were made writable. This was not a test run, and its historical environment
is not reconstructed as qualifying evidence. Exact final-source bounded receipts
supply the execution evidence. Earlier failed packets remain immutable.

The frozen source146 identity remains
`acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d`,
host11 remains `027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2`.
They are historical exact-source identities, never bindings for future changes.
The prior fixed proposal insertion and input custody were rechecked without a
new compiler or whole-source query. All 17 fields, 15 unselected policy fields,
eight unverified claims, three Pending selectors and six Pending upstream needs
remain. FD_BASE, compiler/review/path/packet caps, all actual prices, root funding,
native ownership/image/allocator/diagnostic bridge and all new compiler/layout/
work/storage/retirement bindings stay pending or unselected.

Compiler, product/native runtime, phones, simulators/emulators, UI, screen capture
and computer use were neither started nor touched. No stopped Android v5,
hosted driver, global process inventory, canonical product source, metadata,
Git, publication or delivery operation occurred. No new dependencies were added.
FieldLog immutable separate-repository consumption, native/device/store/operational/
OTA/GA qualification and accountable gate review remain pending. No GA gate passes.

`seal.json` records every other packet file and excludes itself. All packet files
are read-only. The new read-only checker is
`python3 -B verification/swift-guarded-snapshot-prepaid-input-owner-affine-refusal/seal_packet.py --check`.
