# Private ordinary Android coordinator contract

This next implementation slice joins the already implemented ordinary JNI engine
candidate to the concrete `NativeRenderer` V2 candidate. It does not enable the
public Activity, change signed transport, package a descriptor, or claim native
acceptance. Computer use, capture and native runtime tests remain paused.

The coordinator must be package-private, main-Looper confined, and own exactly
one ordinary session and one concrete renderer. No app-supplied renderer, support
proof or environment may replace the native captures. It must reject reentrancy
and operations after retirement. A private test Activity can drive it later;
the current public `MixerActivity` remains unchanged.

For an initial render or an input event, the synchronous transaction is:

1. Capture the renderer's installed assets and actual window environment. Ask
   `NativeBridge.prepareV2` for the ordinary engine candidate. Retain its opaque
   token immediately, before requesting its defensive packet copy.
2. Prepare the concrete renderer from that exact packet and those captures.
   Attach with input/draw gated, obtaining its preallocated attachment journal.
3. Call `validateAttachedV2` immediately before scalar engine commit. No callback,
   asynchronous work, notification or other native mutation may intervene.
4. On scalar status zero, call `finishV2` immediately. Publish the retained packet
   and the coordinator's committed state only after the renderer's prepared swap
   succeeds. There is no fallible allocation or caller callback between commit
   and finish.

The coordinator must distinguish an unattached prepared candidate, an attachment
that returned its journal, an attempted attachment that threw, a known rejected
engine commit, and an unknown commit outcome. `attachV2` can throw before entering
its cleanup handler or after that handler consumes the candidate. A missing
journal cannot distinguish them. Set an attach-attempted flag before the call;
on any attachment throw, abort the retained engine token, then retire both owners
even if abort fails. Do not infer that discard or rollback is valid. This bounded
availability limitation avoids changing the accepted renderer cleanup contract.
A later recoverable-attachment seam needs an explicit disposal disposition.

Before a commit attempt, rejection aborts the engine token and discards an
unattached candidate or rolls back a returned journal as appropriate. The
attach-throw case retires as specified above. A known nonzero commit status cannot
commit the engine; it uses the same cleanup. The old presentation may resume
only when abort confirms status zero and native cleanup succeeds. Closed status
confirms disposal but cannot restore a usable session, so retire the presentation.
An unexpected status, failed abort, thrown commit, or thrown post-commit finish
retires both sides. Never infer that a throwing commit failed before its effect,
attempt rollback after a successful commit, or claim an uncertain old screen is
authoritative. Retirement sets local closed state first and attempts both native
gating/disposal and engine destruction even if one cleanup throws.

If JNI preparation throws before returning a candidate, its internal failed
delivery cleanup may have destroyed the session when abort was uncertain. The
coordinator has no returned status proving that the old session remains live.
Retire on that exception as well. Once the candidate and token have returned,
a later defensive-copy failure can follow the ordinary confirmed-abort path.

A synchronous input callback may already have changed native text or a switch
before engine preparation. Recovering the prior engine/renderer tuple does not
undo that input or restore IME composition. Until a separate retry/rejection UX
is implemented, a failed native-input transaction must retire explicitly after
its transaction cleanup. It must not silently reopen an unacknowledged input as
if it were a committed binding. No synthetic composing-text restoration is allowed.

Environment-only refresh uses the exact retained committed packet, a fresh native
environment and the same renderer prepare/attach/validate/finish sequence. It
must perform no engine prepare/commit, reducer call or new document generation.
An unsupported capture keeps forwarding closed or retires; it cannot label an
old capture current. Automatic refresh scheduling and lifecycle integration are
separate from this synchronous private seam.

Required headless evidence exercises the production coordinator bytecode with
explicitly identified test-only leaf substitutes: successful ordering, all
prepare/copy/attach/validation boundaries, each scalar commit disposition,
unknown commit before and after a simulated effect, abort/rollback/discard/finish
failures, reentrant and retired calls, initial failure, event rejection,
environment-only no-engine behavior, and cleanup that continues after a failure.
Such tests establish coordinator decision behavior only. They cannot establish
real Android view restoration, draw/input gating, IME or JNI execution.

Separately compile the unmodified production coordinator with the actual Android
SDK, renderer and JNI declarations and produce DEX from those exact sources.
Retain a future native integration test that uses actual JNI, the ordinary Swift
registry and native views, but do not run it during the pause. Native transaction
acceptance, public bootstrap and GA remain pending.
