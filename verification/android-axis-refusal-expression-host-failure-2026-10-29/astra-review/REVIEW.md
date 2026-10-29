# Independent Astra review: axis host binding failure

**Conclusion:** run `40909865814`, attempt 1, at `2cea1013151ccc38bb635fb4755793cd25a0bd1b` failed because the verifier treated JSON object member order as value identity. The retained host and budget objects have exactly the expected key sets and scalar values. Python sorted their keys during dispatch serialization; `equal()` compares `JSON.stringify()` strings in insertion order. The first host comparison fails; the budget comparison would fail next under the same implementation. This is a binding implementation defect, not evidence of a changed Xcode selection, widened budget, failed Swift test, or new execution authority.

This independent review used inert local data and source reads in Node REPL, with only fs/promises and crypto imports. It did not import or execute the verifier, controls, delivery helpers, compiler, runtime or any product code. It issued no CLI, Git/gh, network, process, timer-patching, held-process, native, UI or capture operation, and spawned no child agent. Tool version was not exposed or queried. The actual run metadata supplies the recorded revision and tree `830e859979d2ea95335d8cb8ea28ac8caaa0614b`; this is not a claim that the concurrently changing local checkout is identical to that tree.

## Exact evidence and causal chain

The retained files independently match the root-provided identities:

| Evidence | Bytes | SHA256 |
| --- | ---: | --- |
| local/job-123574592818.log | 30,244 | 27db14ebb7b5f5bf0d87e0fc9b7150516a47c6a0ab67430088c232120338f3f1 |
| local/connector-observations.json | 29,446 | 603d48ea65cb3226252b78644fc5b3338101dc0800121efab70670dd732e2087 |
| github-delivery-axis-expression-followup/manual-axis-followup-input.json | 1,802 | 42c593d7fdecbaf7c471acfee1fac16b32c348ecfeffd20ebb1ac673d1cfa620 |
| android-axis-refusal-host-admission-expression-correction/verify.mjs | 18,083 | cb62acbbe45fc98d205e3b7b8dfa0d6cc83975c5e9ca3a0e5227e05d57a1dbad |
| installed android-axis-refusal-host.yml | 6,670 | 8483fbf0b110ab9f1806004f51b857d47eebb46acb9521ee1ee91bbfb5a86dc5 |

The 1,802-byte input file is pretty-printed retained JSON. The literal compact `root_selection` dispatch value is **1,624 bytes**, SHA256 **3af103fcba99e9fd728f40c7642acbd5c9418f73e156ad62a7ce968c18d98874**. It equals `JSON.stringify(JSON.parse(retainedInput))` and matches all five environment payload copies in the raw job log exactly. These are distinct byte identities representing the same parsed selection; do not label the pretty-printed file as literal wire bytes.

The producer in `selection_common_axis_expression.py:280–293` reads the frozen template, changes only selected, dispatch_authorized and source_revision, then serializes with `sort_keys=True` and compact separators. Line 301 places that exact string in `--raw-field root_selection=...`; retained command data and the raw log agree. Workflow line 56 uses JSON.parse on the environment value. The consumer's `verify.mjs:19` compares stringify output. At line 85 the expected host literal starts with runner, while the parsed actual object starts with developer_dir. The remaining five host values and all ten budget values match exactly; both sorted key sets match and both original stringify comparisons are false. No source module execution was needed to distinguish these explanations.

The raw log's lines 156–160 name `Host/tool selection` and identify equal:19, verifyBinding:85 and preflight:156. This rules in object-order mismatch. Exact payload/log agreement rules out a transport value mutation. The first binding step ran, so the prior job-level runner-context validation failure is no longer the immediate blocker in this run. The Apple and Swift steps were skipped, so neither tool availability nor test behavior explains this failure.

## Early-failure evidence boundary

Preflight performs binding at line 156, then sourceSnapshot at 157, then creates the output directory at 158. The host comparison throws before preflight source collection or directory creation. The always-running postflight later calls sourceSnapshot, then fails writing source-after.json because the output directory is absent (log line 184). Its arrival at that write supports completion of that postflight sourceSnapshot call, but there is no persisted source-after receipt or successful pre/post comparison. Assessment fails trying to read root-selection.json (line 216).

The upload action's step conclusion is success, but line 248 explicitly reports no files and no upload; retained connector artifacts is empty. Checkout's post-job cleanup is not proof of verifier scratch removal, arbitrary descendant custody or runner disposal. There are **zero axis Swift test results**: all eight XCTest and eleven Swift Testing methods remain unrun. No Apple-toolchain receipt, test artifact, pre/post source identity pair or cleanup receipt may be inferred.

The six ordinary Engine CI jobs for `40907857341` are recorded as completed/success. That metadata does not substitute for the isolated axis test. The separate root-data-write-refusal.json records a Buffer ReferenceError in the functions wrapper before a Node REPL call. It neither caused this hosted failure nor supplies host test evidence.

## Full equality call-site audit

[equality-callsite-audit.json](equality-callsite-audit.json) lists every call and its original source line: **59 verifier calls + 5 control calls + 12 expression-control calls = 76**. The audited import scope is the current expression-correction verifier and its two local importing control modules. Older sibling verifiers retain their historical identities.

| Current verifier locations | Value category | Required semantics |
| --- | --- | --- |
| 85, 86 | Host and budget objects | Recursive exact key membership and scalar values, independent of object insertion order |
| 123, 168, 176, 179 | Source snapshots and preflight binding objects | Same recursive rule; preserve every nested field, source row and digest |
| 65 | Array of suite objects | Suite/name array order remains exact; object field order is immaterial |
| 52, 101, 109, 134 | Inventory, test names and command argv arrays | Exact lengths and positions; only the existing explicit inventory/result sorts remain |
| All other 48 verifier calls | Scalars | Exact scalar type/value; raw strings, hashes, source text, flags, limits and statuses remain exact |

The control consumers add four scalar and one array call. The expression controls add seven scalar and five array calls. Overall: 59 scalar, ten scalar-array, one object-array and six object calls. This is a source/data audit, not execution of those checks or authorization for an OTA release.

Two contracts must stay separate. First, line 89 computes rootSelectionSHA256 from JSON.stringify(selection); retain that serialized selection identity rather than silently replacing it with a canonical semantic digest. Second, lines 81–82 explicitly call String on attempt/run IDs before equal; that existing normalization is not an invitation for the new comparator to coerce other types.

The current verifyBinding validates top-level selection fields individually and compares host/budget as whole objects. It does not enforce an exact top-level selection key set or validate schema/authority_note. Thus unknown-key refusal claims for this narrow change must apply to compared objects. Do not claim a new global top-level schema guarantee without a separate explicit guard and review.

## Narrow correction and controls

Use a new sibling packet. Replace serialization-based equality with strict recursive JSON-value equality: compare object key sets independent of insertion order, recursively compare every value, preserve arrays positionally and compare scalar types and values exactly. Validate the entire operands before an identity shortcut. Reject undefined, functions, symbols, bigint, nonfinite numbers, cycles, holes, extra array properties, accessors and exotic values instead of allowing JSON.stringify to drop or normalize them. Null-prototype plain data objects may be accepted deliberately under JSON value semantics with the same exact-own-key/descriptor checks. Object.is distinguishing -0 from 0 is a documented fail-closed tightening; it changes no selected positive bound.

Do not merely reorder the host literal, patch the dispatch producer to reproduce the literal's insertion order, sort arrays, omit unrecognized fields, compare selected keys only, stringify with coercion, or weaken any source/workflow/tool/budget/attempt/promotion guard. Such fixes either leave the next budget/roster/snapshot occurrence exposed or reduce the comparison's scope.

Required new controls should be finite and targeted:

1. Preserve the exact captured compact payload and its hash as the failing baseline. In the authorized guarded data harness, feed JSON.parse of those bytes to the new verifyBinding with the captured context and captured workflow SHA argument. It must succeed after the correction; old equal must retain its recorded host/budget refusal attribution. This standalone data control grants no new selection or dispatch.
2. Exercise the actual producer composition: frozen template, the three allowed bound fields, recursive sorted-key compact JSON, parse, verifyBinding. Compare the produced bytes to the retained actual dispatch value. Separately check a newly prepared input against its own exact workflow hash/revision before any future authorized submission.
3. Reorder keys at every object depth, including host, budget, suite objects, snapshot rows and binding records. Equality should hold without mutating either operand. Distinguish this semantic equality from the serialized rootSelectionSHA256 when its input order changes.
4. Remove, add or change each host and budget field individually; unknown keys must not disappear. Include nested objects and arrays-of-objects, empty objects, and missing versus explicit null. Every difference must refuse.
5. Preserve arrays strictly: reorder, append, remove or duplicate a suite, test name, source row or argv item. These must refuse wherever the callsite expects order, while existing explicit sorting remains unchanged.
6. Probe numeric strings versus numbers, booleans versus numbers, false versus null, finite-number changes, -0 versus 0 under the selected contract, and all rejected non-JSON shapes. Identical invalid references must still refuse. Malformed JSON must fail at its parse boundary.
7. Preserve source manifest/review/projection and workflow byte hashes; mutate each representative hash, source text, revision, repository, event, attempt, profile, tool identity, file/output bound and promotion flag. None may gain acceptance from the object-order correction.
8. Re-run the existing parser controls only under newly authorized guarded data execution and retain their original attribution. Do not count them as Swift tests. Keep the historic expression proof unchanged: its line 55 permits only an admissionRelative change and therefore cannot certify a comparator edit. A distinct sibling-specific source-delta proof must identify the exact comparator replacement, allowed sibling path changes and otherwise unchanged guards.
9. Exercise an early binding refusal as data to ensure it is reported as preflight failure, with no test/artifact/cleanup success inferred. Any future failure-envelope or postflight-gating improvement is a separate reviewed change, not a reason to suppress this failure.

The decisive next integration is the guarded exact producer-to-consumer data control. Root can then reconcile the corrected source. A hosted replay requires a separately selected allowance; this review provides none. Avoid another preparation-only loop once the bounded correction and its data controls are available.

## Decision to close the admission-defect campaign

The comparator correction, exact producer-wire regression and distinct allowed-source-delta proof are sufficient in scope to resolve the diagnosed defect, subject to their actual guarded controls and independent source review. There is no evidence for changing host selection, budgets, package scope or retry policy, or for another generic design/review layer.

Before a new host selection, perform **one composed data-only preflight** with the exact candidate workflow bytes, actual frozen 27-member package plus manifest/review/Apple-probe source bytes, and the intended producer-serialized selection/context. It must traverse verifyBinding, sourceSnapshot (including roster equality at line 65), and receipt writes into an owned data fixture; reparse those receipts and check the binding and serialized rootSelectionSHA256 identity. Use an admitted filesystem adapter or owned fixture, with no Apple/Swift invocation and no live workflow installation implied. This guards the untested composition beyond a direct verifyBinding call without consuming a hosted attempt.

The captured old wire regression proves the old boundary; a future payload must separately bind its own final delivered revision and workflow hash. After these finite checks pass and root reconciles the result, close this source/admission campaign. Actual Apple tool availability, Swift compilation/discovery and all 19 named methods then require a separately authorized bounded host run. Their presently unknown outcomes do not justify another preparation-only cycle. This review grants no new host selection or allowance.

## Recurrence and preservation

The previous 47 controls included `structuredClone(template)` at controls.mjs:45 and a direct verifyBinding call at 47. That clone preserved template key insertion order. The 18 expression controls checked source placement and exact deltas; their retained receipt states the prior 47 were not rerun. Neither covered the actual producer's Python sorted serialization. This is a missing composition test, not evidence that those controls executed falsely. Their results retain their original limited scope.

All **52** retained delivery/helper command records were independently read: nine preflight, 22 delivery, five Engine binding, five axis binding, seven dispatch and four late binding. Every retained record reports admitted, exit zero, direct child reaped, owned group absent, stdout EOF and stderr EOF. This verifies stored data, without new process/kernel/pipe observation. The selected 174-row historical source object data and its digest `8f2dc2b28d7279f9df9189a14adf2cdfdcbd016e768473ad0ea522f590b4b5fb` stay preserved. The data file's actualStagedObjectsObserved field is false; no new staged-object verification is claimed here.

The sole manual allowance is consumed, with one dispatch and zero retries. No replay, new helper/delivery command, source-pair promotion, canonical installation, native run, OTA/GA acceptance or release is authorized. Existing frozen packets and all native/process/custody holds remain. Output ownership is only this astra-review directory. The attached seal binds the report, full call-site audit, observations and source/evidence identities; it does not upgrade a diagnosis into a test pass.
