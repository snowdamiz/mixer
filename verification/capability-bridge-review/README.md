# Independent experimental capability bridge review

Candidate 5 passes this bounded independent review. No unresolved source finding
remains within the reviewed experimental contract. The review modifies only this
directory; production source, credentials, trust stores and devices were untouched.
`final-receipt.json` binds the source, original tests, exact commands, raw outputs,
labelled derived mutation maps and audited implementation-owner evidence.

The reviewed 55-input source freeze is
`070f626acd4cfc99ec2bdeb9b1e1dc45da228548d3f6458fb8fbe1b7bbca4b4d`.
Its production `Ownership.swift` SHA256 is
`00601bbfab179a60e5ea31e96dc886b1bf9240b205ccd9dfbdb66877dc150bf9`.
The immutable export is the implementation owner's
`experimental-capability-runtime/.build/qualification-2026-10-23-candidate-5/source`.
The single host archive is
`experimental-capability-runtime/build-verification/local/qualified-final-v3/host/lib/libmixer_vm_capability_experimental.a`,
SHA256 `a015ff65980422dd0b9c5cad2e28741d1e5ba478e0f657dcaedf75477d553b72`,
built from native revision `b25e3b7de2391a80d12e7fd75e60903495bec120`.
Both staged C headers match that committed revision byte for byte. Source/export,
archive and header hashes were checked before and after each review command.

| Evidence | Executed result |
| --- | --- |
| Unmodified public Swift consumer | 10 XCTest cases in debug and release |
| Labelled derived ordering/lifetime consumer | 14 XCTest cases in debug and release |
| Metadata faults, separate process | 1 case with wrong ABI and invalid i32 per mode |
| Ambiguous creation, separate process | 1 case with 3 faults per mode |
| Public and derived Thread Sanitizer | 10 and 14 cases; no reported race |
| Owner receipt audit | 55 source inputs, 18 command logs, 16 staged native artifact bindings, 4 actual linked binaries, 3 real negative TLS fixture receipts/full logs |
| Actual verbose public Swift link commands | Exactly one experimental native archive; no MixerRuntime/default archive co-link |

The public target imports only public SDK/experimental products and uses original
Wasm fixtures. Its primary effect path is the concrete AppPrivateKeyValueStore:
disabled-startup rejection, put binary, get, delete, get missing, put empty, get
empty and delete through the fixed guest wake. It compares exact canonical guest
wrappers and the private store, then joins all seven acknowledgements. Other
public cases cover real inline policy-denial callbacks, malformed arguments,
17 simultaneous synchronous prepare calls, abandoned/cancelled/one-shot
constructions, ordinary native rejection, ready-guest fairness, and failed
originating turns that start no concrete storage effect. Test-side retries only
wait for the public command slot; production admission is never retried.

The separate derived target delays real events and invokes existing SDK internal
storage scheduling controls; it grants no adapter authority and supplies no fake
successful result. It tests acceptance publication, result/actual-exit ordering,
late payload after expiry, one admission worker, bounded close cleanup after eight
raw takes and exhausted budgets, close around reservation/waiter handoffs, and
strong independent exit-owner retention after public close/deinit. Four close
races assert `status.failure == nil`: late take registration, wake, pre-admission
remaining query and accepted-work exit/deadline confirmation. The accepted-work
case also asserts it was never relabelled as local no-I/O. Constructor fault
probes deliberately quarantine capacity while proving the captured input buffer's
custom deallocator runs. A hidden zero native handle in one filtered fault process
remains conservatively retained until that process ends. This is not an OS or RSS
reclamation claim. See `InternalHarness/README.md` and `candidate-5/derived-map.json`.

An initial candidate-1 public test incorrectly expected an empty guest import to
produce a C Call; the import rejects length zero before token issuance. The test
was corrected, and empty native Call validation moved to an explicitly derived
metadata case. The first internal compile failed only for two weak local variable
warnings under warnings-as-errors; holder objects corrected the test. All original
failure outputs and exact attempted inputs remain under `candidate-1/`.
Candidate 1 later passed the initially written suites, but the additional normal
close diagnostic assertion exposed a production defect: a late real take followed
by close drained yet set `failure = invalid_arguments`. Its exact failing probe is
`candidate-1/internal-replay-3/`. Candidate 5 adds checked-closed-status-3
classification at drain/wake/both remaining-query catches and checks closed
between takes. Metadata, status 4 and ack errors retain their fatal/conservative
handling. Only Ownership.swift production bytes changed from candidate 1;
verify.py separately gained stricter counts and linked-binary bindings. The final
candidate-5 matrix includes the regression and the three additional close races.

The implementation-owner receipt audited here is
`experimental-capability-runtime/verification/2026-10-23-candidate-5/receipt.json`,
SHA256 `6194e77ab6119f2d91d18f0a374a04fc99bd018019ae9c1e1a81e6e3e02fd07e`.
It records 16 tests per debug/release/TSan mode, a separate one-test observational
16-idle-owner measurement, and official iOS arm64, iOS simulator arm64 and Android
arm64 public consumer compile/link. The linked binaries and architectures were
independently hashed/audited; no platform execution is inferred. Its real
untrusted loopback TLS fixtures observed TCP acceptance and TLS failure with zero
application requests. They establish normal-trust rejection only. The separately
pinned builder receipt is reused rather than repeating Rust or platform builds;
root independently reviewed its CLI/source extraction and mixed-registry evidence.

Reproduce only with the stated immutable export and staged archives present:

```sh
python3 verification/capability-bridge-review/run-public.py --candidate 5
python3 verification/capability-bridge-review/make-derived-review.py \
  --source-root /absolute/path/to/candidate-5/source \
  --source-manifest verification/capability-bridge-review/candidate-5/source-manifest.sha256 \
  --manifest-sha256 070f626acd4cfc99ec2bdeb9b1e1dc45da228548d3f6458fb8fbe1b7bbca4b4d \
  --destination /new/external/review-workspace/derived
python3 verification/capability-bridge-review/run-internal.py --candidate 5
```

Drivers refuse to overwrite prior receipts; explicit replays preserve separate
output directories. The internal runner uses the derived tree beside the public
receipt's recorded workspace. The map records every injected source/test/resource
hash. Existing archived outputs are evidence, not a request to rebuild them.
`PREPARATION.md` and `preparation.json` record the earlier preparation state only.

These results are macOS host execution plus audited cross compile/link. The pinned
Rust archive and system frameworks are uninstrumented by Swift TSan. Logical byte
and worker counters exclude allocator backing, transient DTOs, runtime/framework
lifetime and actual Task destruction. The cooperative budget can overrun by one
admitted operation; no hard real-time, global process resource cap, no-OOM,
no-unwind, rollback or OS-resource-destruction claim is made. Normal-trust HTTPS
success with an explicitly provisioned fixture, physical iOS/Android, release
activation, immutable external dogfood, identity, publication and GA remain
outside this review. No trust bypass or device operation was attempted.
