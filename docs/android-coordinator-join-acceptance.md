# Ordinary Android coordinator native checkpoint

The private ordinary Swift/JNI/coordinator/native-renderer join now passes its
bounded development matrix on the API37 arm64 emulator: **eight operations and
64 native checks**. Root independently validates 56 saved runtime artifacts,
60 evidence bindings and seven exported ordinary engine packets. See the
[root acceptance](../verification/android-coordinator-join-root-review/native-join-acceptance.json)
and [actual runtime receipt](../verification/android-coordinator-apk-packaging/runtime-1/receipt.json).

The exact installed APK is
`78af8c5df197fb6f163f3010825648a1b1a50427c9ab963b1c5aeca1e513b3ba`.
Its 105-input closure is
`00c269c70199ffb376b39394db1c2367f8e9053d92ce6a863741d2a154359c04`;
all 88 production source/data inputs match the current checkout. Production
classes, Swift/JNI/native libraries, resources and manifest bytes are unchanged
from the original joined build. The correction changes the test assertion and
APK packaging, with fresh ephemeral debug signing. No production key is used.

| Actual operation | Observed result |
| --- | --- |
| JNI | Ordinary registry ownership, candidate copies, busy/foreign/stale/closed statuses, abort, one-use commit and committed Swift state pass. |
| Initial presentation | The actual packaged descriptor and attached environment produce the ordinary checklist in native views. |
| Toggle callback | `performClick()` returns false with no click listener, while the checked listener commits revision 1→2 once and the surviving native control agrees. |
| Text connection | Real native `InputConnection.commitText` commits `joined`; native buffer and Swift packet agree at revision 3. |
| Environment refresh | Exact committed packet identity/bytes and a real pending registry candidate survive; no additional prepare token is allocated; stale capture closes forwarding and fresh capture reopens it. |
| Attachment failure | The concrete attachment fault retires native and Swift owners and closes forwarding. |
| Activity lifecycle | Actual destruction disposes the live coordinator/session/renderer; relaunch creates a fresh revision-1 session. |
| Rejected input | Swift rejects malformed input, retires the joined owners and rejects later operations. |

Root independently decodes the seven exported packet byte streams and verifies
revision/state changes, surviving identity generations, environment byte equality
and fresh relaunch state. The native software `View.draw` probe is included;
hardware/compositor paint and visual parity are separate checks.

Two initial attempts failed before emulator boot. A per-process
`-feature -WiFiPacketStream` launch fallback resolved the observed startup hang.
The next run exposed a test assertion that confused `performClick()`'s click
listener return value with checked-state delivery. The corrected fixture then
exposed compressed `resources.arsc` during installation. All failures remain
preserved. The final packaging guard checks actual local ZIP offsets and storage
methods before native work and again before install; official `zipalign` and
signature checks pass. Root separately replays 44 host runner/cleanup/packaging
checks. No failed attempt is relabeled as a pass.

The owned PID/group 31099, including its new child processes, was stopped;
ports 5586/5587 were free, and the 177-file extraction (172,885,588 bytes) was
removed after an empty holder check. A fresh process check confirms the unrelated
Morse emulator and its netsim service remained running. Original builder scratch
from the earlier frozen build is outside this runtime-cleanup claim.

This accepts the private API37/default-environment development subset. Actual
pointer tap/hold/drag/scroll delivery, system keyboard/composition, accessibility,
complete native fault/lifecycle coverage, other OS/resource profiles, shared
iOS/Android appearance parity, public V2 and signed transport remain pending.
Physical phones are deferred to final acceptance, as authorized. Published
separate-repository FieldLog, store/customer/operational and GA gates remain open.
