# Private Android owner independent implementation review 1

Frozen candidate 2 is **not acceptable for implementation acceptance**. This
bounded review confirmed three additional runtime defects, two mandatory source
obligations, the previously reported input-ledger defect, and the subsequently
reported cleanup-mode defense gap. Root authorized repairs; no repaired product
bytes were inspected. Full matrix qualification remains pending.

The admitted candidate manifest is
`dc75c6544fdc10d25457c00782dcfb8afbcde756988ce0fd742606bb69c8c0e7`
(1,170 members, 11,537,811 bytes). The admission receipt
`77f257671008d2d6dc51530b8b3d3f954c4ce3f75eeb9edc6257a3b10805df42`
is overridden by the hold
`f719fe06f8e162ab99de087157bf69a461b6a195bbdcdd79a497166d71bd9c77`.
CLI/profile literal migration and consumer qualification remain held. Selected
dirty/result clarification `2a1574cea4d94b21bbf5d59b64484700ca7dcdf8d94fd3822fdf8fb63c5f0fa4`
remains mandatory.

All source anchors below refer to the retained
[candidate-2 snapshot](../verification/android-private-owner-independent-review/implementation-review-1/candidate-2/source/native/android/),
never mutable product files. [Findings](../verification/android-private-owner-independent-review/implementation-review-1/findings.json)
give the evidence class, exact paths and expected boundaries.

| ID | Finding and scope | Frozen anchor / independent evidence |
| --- | --- | --- |
| F01 | Known input ledger defect: an ordinary returned cancellation is labeled `IN_PROGRESS` while transaction/report activity continues. Source corroboration; root reported it before admission. | `NativeOwnerV2.cancelInput`, lines 220–228; `busyForOwnerDisposal` includes active/report work. |
| F02 | Fresh native-input focus acquisition does core invalidation before scalar sealing. At the actual `Handler.post` callback, real core is dirty/unfocused while shared draw/input and current gate remain open. Nonterminal `SEAL` is ignored by `process`. | `nativeInput`, 169–181; `seedFocus`, 185–190; `process`, 249–256; [targeted-2](../verification/android-private-owner-independent-review/implementation-review-1/targeted-2/03-fresh-input.stdout), repeated in targeted-3. |
| F03 | Actual `Gate.invalidate` cancellation reenters `owner.close`; `onResume` then continues ordinary focus/window readiness probes. This violates the selected terminal boundary. Real core stays retired; no authority reopening or new operation was observed. `start` and `Work.run` share the source pattern and need separate corrected controls. | `onResume`, 117–123; `start`, 109–112; `Work.run`, 63–65; [targeted-3](../verification/android-private-owner-independent-review/implementation-review-1/targeted-3/03-terminal.stdout). |
| F04 | Renderer-only fixture registration/construction and nonprimary-root factory lack failure unwind. The fixture close path also needs independent cleanup if core close throws. Source-only private native-fixture review; no instrumentation runtime was started. | `NativeAppearanceV2Instrumentation.RendererFixture`, 48–53, 75–80; `newRenderer`, 83–87. |
| F05 | Seven helpers recapture `Mutation` instead of accepting the selected explicit scope parameter. Recursive/group/live callers must propagate the same captured scope. Existing transaction equality often yields the same object; this is a mandatory source-contract deviation, not a demonstrated authority-minting bypass. | `Record` 139, `bind` 222, `measure` 389, `measureList` 533, `installChildren` 579, `layoutRoot` 595, `layout` 603; correction lines 288–298. |
| F06 | `Handler.post` enqueues then throws at its supported before-return hook. `post` discards the exact Work identity before terminal cancellation, so no `removeCallbacks` is attempted although handler ledger says `RETURNED`. One stale delivery remains; it executes inertly after retirement. | `NativeOwnerV2.post`, 318–328; `cancelQueued`, 330–335; [targeted-5](../verification/android-private-owner-independent-review/implementation-review-1/targeted-5/03-post-failure.stdout). |
| F07 | `Mutation.require` permits `CLEANUP` on sealed flags, while ordinary helpers have no mode refusal. Root/producer reported this later; independently source corroborated. No production `Mutation.cleanup` caller exists in candidate 2, so this is a defense/source obligation rather than a reached production bypass. | `Mutation`, 66–76; ordinary helpers; correction 283–298. |

The exact fresh-input path is real native `InputConnectionWrapper.commitText` →
TextWatcher → renderer input event → owner. Its first owner focus acquisition is
distinct from lifecycle entries that seal before probing. A raw focus fact changes
at the actual event's final captured focus return; no listener, token, core or
expected renderer substitute was fabricated.

The terminal witness reenters only at actual renderer cancellation
`Gate.invalidate`. Subsequent observed ordinary probes are `hasWindowFocus`,
`isDestroyed`, `isAttachedToWindow`, `getWindow`, `getWindowToken`, `getWidth`,
`getHeight` and `getRootWindowInsets`. They are readiness probes, not consumed
release/hide cleanup. Draw/input remain false, prepare count remains one and
destroy count is one.

Three positive controls have concrete value alongside these failures:

- Lifecycle focus invalidation reaches `Handler.post` with shared/current gates
  already closed and the actual core dirty/unfocused.
- [Completed successor input](../verification/android-private-owner-independent-review/implementation-review-1/targeted-4/03-accepted-input.stdout)
  returns `true` across real synchronous successor publication. Two actual
  prepare/commit operations complete, packet revision is 2, real core is LIVE,
  and the operation token clears. The descriptor and both packets are independently
  authored against actual decoders; producer witnesses were not imported.
- [Observer registration failure](../verification/android-private-owner-independent-review/implementation-review-1/targeted-6/03-registration-failure.stdout)
  throws after actual final-slot acquisition, then encounters an independent fatal
  removal failure. All eight exact removal slots are attempted once. The uncertain
  failed slot is preserved, owner and observer retain both original failure
  identities, fatal escapes after cleanup, core is retired and JNI create is zero.

Every compilation uses the exact 14 selected actual subjects plus the 73 admitted
mechanical Android/JNI substitutes, the admitted leaf-3 probe, and one independent
test source. There are no product source overlays. The private fixture and public
routing sources are separately retained source-review inputs, not compiled native
runtime evidence. Core bytes match
`4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6`.
Public `MixerActivity`, `NativeBridge`, installed descriptor decoder and the
unchanged resolver/geometry/parser/toggle subjects match the sealed accepted
baseline. This does not substitute for the pending five V1 positives, SDK projection,
profile/CLI or native qualification.

[Runtime frame bindings](../verification/android-private-owner-independent-review/implementation-review-1/runtime-frame-bindings.json)
bind all 33 retained targeted frames to actual compiled class hashes, JVM
descriptors, bytecode instructions and line tables. Every original run's relevant
class bytes equal the supplementary reference compilation. This is identity
evidence for these witnesses; it does not resolve all baseline/new matrix sites.

[Historical authored source map](../verification/android-private-owner-independent-review/implementation-review-1/historical-authored-source-map.json)
retains each exact driver version and runner. Targeted-1's wrong anonymous-class
selector is preserved as a reviewer setup failure, not a product finding. Later
focus/terminal/post assertion failures are retained alongside successful controls.
Supplementary targeted-7/8 compile and disassemble only; they run no product cases.

The official local tools are OpenJDK 27, with strict `javac --release 17 -g
-Xlint:all -Werror -proc:none`, empty class/source paths and explicit source lists.
Java 17 target compatibility is not a JDK 17 runtime claim. Exact argv, executable
hashes, tool versions, input/class hashes, stdout/stderr, exit states and cleanup
are retained. Each child has 120 seconds, 2 MiB per stream and one owned process
group; Java has a 256 MiB heap. All observed children returned and were reaped;
exclusive scratch was removed. No native, UI, capture or process discovery ran.

The sealed 30-family plan remains unchanged: all 184 baseline V2 sites × seven
cases, additional introduced sites, five separately labeled unchanged V1 positives,
Closure A owner/core/coordinator/Observer coverage and Closure B actual 14-body
coverage remain mandatory. This packet runs six distinct targeted controls, with
repeated failures/controls retained; **it does not complete the site matrix or
all-family coverage**. The next frozen candidate must rerun repaired witnesses and
complete the existing plan using exact source/descriptor/BCI mappings. Producer
progress counts are not independent oracle evidence. CLI, native/device, public
V2 and GA acceptance remain unqualified.
