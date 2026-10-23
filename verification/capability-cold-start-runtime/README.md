# Experimental cold-start coordinator evidence

This additive facade selects only through its private v3 durable store and the
same installed material/context. The five `CapabilityColdStart*.swift` files
compose the exact `f5d99d1ea1595c431d87c99d110eb2bd4acd5b4c` baseline with the
separately frozen concrete attempt/retirement files. They expose no artifact,
selection, validator, adapter, native handle, token, or public export-invoke input.
This remains an experimental cold-start slice, not general guest UI event delivery.

`CapabilityColdStartRuntime.open(configuration:execution:)` acquires the outer
16-owner reservation before store/adapters/I/O. Downloads admit one ordinary
operation before exact owned byte copies (64 KiB per signed document, 1 MiB per
chunk); cancellation has one separate bounded ingress. Selection is one-shot:
downloads and another start are rejected after selection begins. No caller task
or async actor queue is used as an unbounded input buffer.

Startup consumes one private selection, binds an I/O-free concrete owner before
construction awaits, runs startup with effects disabled, records durable intent,
then enables with the original monotonic cutoff. Installed milestone reports and
a fresh monotonic observation interval are both required for healthy publication.
One one-shot timer re-pokes the existing weak-worker notification consumer. Busy
ordinary tails re-poke that same consumer; notification callbacks create no Task.
The timer and exactly one consumer are joined on every unwind independently of
actual native drain. The timer cancellation continuation can retain its one
counted waiting frame; this is not a claim about runtime Task destruction.

Close/deinit latch local stop before native cancellation. One coalesced close
job joins the observation/ordinary logical tails, records an existing terminal
with `allowFallback: false`, and closes the store. It does not await native drain.
The separate adapter obligation remains counted until exact bridge and concrete
retirement; `cleanupPending` is diagnostic and cannot authorize reuse. A checked
failure before effects may select at most one retained healthy fallback, only
after old concrete aliases have left an inner helper and actual retirement has
completed. Any failure after effects requires recovery without live fallback.

Run from the repository root (fresh evidence names):

```sh
python3 -B verification/capability-cold-start-runtime/run.py --name host-replay --all-tests
python3 -B verification/capability-cold-start-runtime/run.py --name derived-replay --derived
python3 -B verification/capability-cold-start-runtime/supplemental.py --name consumer-cross-replay --candidate host-replay
python3 -B verification/capability-cold-start-runtime/audit.py
```

The drivers compile only the activation target against pinned retained dependency
objects/modules from transition candidate3. They create no SwiftPM/Rust graph,
link exactly one experimental native archive, and record commands, logs, source
exports, module/binary hashes and limitations. TSan is launched directly with the
official runtime; Rust and platform internals are not TSan-instrumented.

`2026-10-23-candidate-1` runs all 95 functions in Debug, Release and TSan. These
are 81 baseline tests, six concrete tests and eight new coordinator tests.
`2026-10-23-derived-final` runs the eight coordinator tests plus five original
captured-source scheduling/integration tests in each mode. Its patch adds two
async gates, a data-only retirement-publication gate and an internal export
driver only in copies. Real signed verification, native VM, durable commits and
concrete storage remain unchanged. The delayed publication test pauses **after**
actual bridge/KV close; it does not reproduce hung native I/O. Enabled KV and
wake-trap results using the derived driver do not qualify a public event API.

`PublicEmbedding.swift` is an ordinary-import example: real native embedding
events should call `nativeFeatureDidStart` and `nativeFirstScreenWasPresented`.
Startup never calls those methods automatically. Its executable smoke has no
signed candidate and runs native fallback; it compiles the observation callbacks
without pretending a real feature/screen occurred. Three compile negatives reject
artifact ingress, public invoke and private selection access in both modes.
Official iOS/Android module/object checks are compiler evidence, not app links or
physical-device receipts. No device, FieldLog, publication or GA gate is passed.

All initial experiments remain intact. `development-linked-1` had only a test
weak-variable warning; `development-derived-1` asserted the wrong diagnostic
spelling; `development-derived-2` omitted a signed storage grant in its queue
fixture. Supplemental attempts preserve wrong iOS module-map path, Android
single-output/multithread flags, and a script-local scope error. Later checks fix
the harness/tooling only; production bytes remained frozen throughout.
