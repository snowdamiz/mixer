# Independent owned-enable cutoff review

Scoped approval with no open actionable findings. The new SPI is restricted to
owned sessions and carries the exact caller-supplied DispatchTime uptime cutoff
through the existing one-command slot. The guest worker checks `now >= cutoff`
before C enable. Local expiry is outside the generic native-error catch, records
the fixed typed `startup_deadline` / `deadlineExceeded` / `enableEffects` failure,
and starts ordinary cleanup without misclassifying nil native status as quarantine.
The legacy enable path has no cutoff and retains its previous behavior.

The frozen base manifest is
`9e754a25364c5751e209be1f6f535300d435fee01328e0cbaf87ee097bd4940f`
(72 inputs). Root's complete 35-test Debug/Release/Swift-TSan matrix passed against
that export. Its separate newly added consumer then failed because its original
minimal Wasm omitted required memory/wake shape; that failure remains preserved.
Root repaired only that consumer fixture, froze the same 72 paths under manifest
`8f4299cc87754cc2410fef79828883701944ff2cad58e8a2800f25330ac7a842`,
and rebuilt all four platform targets/eight consumers. Both host consumers ran,
including actual successful owned enable. Runtime, tests, SDK and docs are exact
between the base and repair. This review audits that composite evidence and does
not describe the original failed consumer receipt as an all-green qualification.

Original `PublicProbe.swift` uses SPI without `@testable` against the retained
unmodified Debug and Release products. Fourteen checks pass in each mode: future
cutoff executes actual Wasm/concrete KV and persists exact bytes; zero cutoff
reports the fixed typed local failure before actual retirement; every one of the
sixteen construction permits is reusable; non-owned SPI rejection leaves legacy
enable usable; actual startup-trap first failure is preserved; and an already
closed owner rejects without fabricating a deadline failure. The ordinary-import
compile rejection confirms the new method remains SPI. Dedicated sinks have no
strong owner/group/session back-edge and no adapter alias is retained for work.

The separately labelled derived executable compiles the exact seven frozen Swift
runtime files as one review module, linking retained SDK objects and the unchanged
qualified native archive. Three test-only edits count immediately before actual C
enable, command admission and concrete cleanup Task entry. No native result,
enable, exit or acknowledgement is fabricated. The manual private owner assembly
uses actual C create and concrete host/KV; it does not test public construction
handoff, which the unmodified public probe and prior lifecycle review cover.
This adds no package graph or Rust rebuild.

Four isolated derived cases pass in both Debug and Release, 28 checks per mode:

- Eight queued-expiry checks hold the guest queue until the exact admitted cutoff
  expires, observe zero C-enable entries, first terminal notification before
  cleanup Task entry, one cleanup, actual final retirement, no quarantine and
  complete sixteen-permit reuse.
- Six future/legacy checks observe C-enable counts one and two for their
  respective paths, real KV bytes, and no C enable on non-owned SPI rejection.
- Seven checked-failure-first checks deliberately stale an internal handle before
  normal close. The real checked native close status3 wins while enable is queued;
  queued enable rejects closed, the first failure remains immutable, C enable
  stays zero, and failed native close retains its reservation without retirement.
- Seven deadline-first checks inject the same private stale handle but let local
  expiry win before the later checked close failure. The deadline remains first,
  its terminal callback precedes cleanup, C enable stays zero, and the failed C
  close prevents false retirement. Neither checked3 nor local expiry is treated
  as quarantine. Both fault cases are isolated subprocesses and deliberately
  violate private native ownership; they are not public reproductions.

For a failure that is itself discovered during native cleanup, notification can
follow cleanup Task entry. It still precedes `closeFinished`, so final drain cannot
overtake it. Normal-close versus expiry priority is sampled: an already closed
worker rejects, but a concurrent close can race the separate closed read and time
sample. The approved contract does not promise atomic normal-close priority or a
hard real-time boundary across instructions/C execution. Existing checked first
failure always wins. The future coordinator must durably record effects intent
before this call and retain that intent conservatively if enable fails.

`finalize.py` verifies actual frozen/live source, the repaired-only fixture delta,
logs, native artifacts, reused products, all derived edits/inputs and binaries.
`final-receipt.json` binds the resulting source/evidence manifests; cache components
are excluded. This review had no compile or test failure and changed no production,
old lifecycle seal or owner evidence. Swift TSan evidence is the root matrix;
the derived probes are Debug/Release. Rust and platform frameworks are not Swift
TSan instrumented. Cross targets compile/link only, with no physical-device run.
No durable coordinator, authority/health, hard global resource cap, Task/allocator/
OS destruction, trust/credential change, production, publication or GA claim is
added. Root owns commit/push.
