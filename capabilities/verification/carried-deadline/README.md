# Carried absolute deadline prerequisite

`CapabilityHost` now accepts
`submitObserved(_:noLaterThan:deliver:didExit:)` for concrete installed adapters.
The provided `ContinuousClock.Instant` narrows the existing operation/default
deadline with `min`. Time before host acceptance is not renewed. The original
observed overload shares the private acceptance path with no added cap and
retains its behavior. No bridge or guest integration is implemented by this slice.

The existing deadline checks before adapter invocation and at completion use the
same selected absolute cutoff as the watchdog. A cap already elapsed at acceptance
does not invoke an adapter; explicit no-I/O adapter exit still joins invocation
return before the exit callback and eventual capacity release. Terminal delivery
remains separate from native exit, and the first terminal result stays immutable.

Six public-API tests use a real `AppPrivateKeyValueStore` installed in the host:

- A put with an expired cap delivers one `deadlineExceeded`, reports one exit,
  creates no storage namespace/key, and permits the next capacity-one generation.
- A synchronous delivery callback holds host actor admission until a caller's
  preexisting deadline has elapsed. The later accepted put cannot renew that
  budget and does not create its key.
- A test-only isolated function holds the concrete storage actor while work is
  queued. A 100 ms carried cap wins against the 2000 ms host default; a far-future
  cap cannot extend a 50 ms default. Deadline delivery precedes native exit, and
  capacity remains occupied until the invocation returns.
- The old observed overload still enforces its default and retains the same exit
  join. Timely success through the new overload survives its later cap and close
  without another delivery or exit.

The test-only gates use bounded condition waits and unconditional release. They
do not replace production clocks, native adapters or host methods, and the test
target imports only the public module. The storage gate is an isolated Swift
function in the test target, without an SDK test hook or extension. No claim is
made that an operation cannot produce side effects if it suspends after its
pre-invoke check. Deadline failure does not roll back a durable effect.

`receipt.json` records 63 source inputs, exact command/output/tool identities,
source freeze, scopes and limits. The final source-manifest SHA-256 is
`57f9b61d33d5171fa02726169cce994e4578949c6179af5519f078b56ef6f5ad`.
Both full macOS modes pass 51 tests; the native HTTP, exit and deadline selection
passes 31 tests under Thread Sanitizer. Official iOS arm64, Android aarch64 API28,
and WASI builds pass, as does Java identity compilation. Platform builds are
compilation evidence, with no target execution. Framework internals are not
sanitizer instrumented. Phones remain disconnected and no device commands ran.

Only native identity outputs changed during regeneration. Native implementation
identity moved from
`25a597ec0162a42e9d13b737d66cce2a7fe888e781b97490ded8991c9bb84b9a` to
`4fcc770e62d39b415e657ce03aa11fa7fb83ee8bfe1a99567716e9b4372d1c59`.
The 58 source inputs outside the five owned implementation/test/output paths
are byte-identical to the recorded base. Signed semantic contracts, schema
capability hashes, all generated codec/model bytes and existing tests are
unchanged. This requires the updated installed native implementation; it adds
no activation or release authority.

Reproduce from the repository root with:

```sh
python3 -B capabilities/verification/carried-deadline/verify.py
```

The driver reuses the existing separate scratch directories for each mode. It
preserves earlier changed logs and receipts, including the first full successful
run before the driver was refined to support already-regenerated identities.
There were no failing implementation-test experiments in this slice. The initial
focused development run also passed all six new tests; the recorded full suites
repeat them. Historical `host-deadline` and captured deadline-review evidence is
untouched. This is implementer evidence; independent review and root approval are
separate. No C/VM, registry, executor, guest bridge, activation, device, published
package, store binary, FieldLog or GA gate is qualified here.
