# Native packet v1 encoder: root implementation scope

This additive SDK operation serializes the existing native packet shape from one
immutable `UIRenderSnapshot`. It is a data operation with no presentation, input,
JNI, signed-release or health authority. Its standard UI-v1 bounds do not widen
the narrower signed guest subset or the Android adapter's supported profile.

The root integrator clarifies the stage5 design's phrase “exactly once per node”
as exactly one wire identity record per document node. The encoder intentionally
makes two bounded passes over the same immutable snapshot: the first measures
all escaped output bytes before allocating output `Data`, and the second writes
them. Each pass reads the existing identity; neither reconciles, generates a new
identity, mutates the snapshot nor invokes application code. This clarification
does not modify the frozen JNI proposal or its original acceptance receipt.

Independent review found that the existing in-memory validator checked only
already visited nodes before queuing children. A custom-limit comb could retain
more pending nodes than the standard limit before rejection. The repair checks
the next depth and remaining total admission capacity before appending children,
and removes the temporary mapped child array. At each iteration, processed plus
pending nodes is at most the configured node limit. Limits are validated as at
most 65,536 nodes and depth 128; subtracting processed and pending counts cannot
underflow under that invariant. The standard encoder uses 4,096 nodes/depth64.
This is a bound on logical traversal entries, not allocator capacity or RSS.

`candidate-1` preserves a failed system Java launcher check. `candidate-2` passed
SDK and interoperation checks before independent review found the frontier bug;
it is not the final repaired qualification. `candidate-3` freezes the repaired
validator, encoder, nine focused tests, production Java decoder and public Swift
consumer. Its receipt records commands, tools, exact source hashes and outputs.
The Java run verifies 16 assertions against nine emitted packets and returns
three events to the original Swift snapshot. Existing Android baseline rejection
is deliberately retained and exercised. Full UInt64 generation encoding is a
separately labelled internal Swift fixture; public tests do not claim 2^64 inserts.

Only an exact final independent receipt and root acceptance can qualify this
slice. The existing ordinary Android engines still have their older encoders;
using the SDK operation there is a separate integration change. Actual Java
widgets/JNI, shared styling, signed observation, devices and GA remain pending.
