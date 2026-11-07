# Concrete Android host leaves

This lane owns only `native/android/tests/NativeOwnerV2ConcreteHostLeaves/**` and
this evidence directory. The closed source list is exactly the 73 substitute
FQCNs plus `ConcreteHostProbe` in Closure B of the amended required roster.
None of the fourteen real product subjects is replaced. There is no Android jar,
implicit source path, dependency, product authority decision, installed capture,
environment capture, expected decision log, or fake product implementation here.

`attempt-7/result.json` records the latest successful strict complete-source
compiler check. Attempts 1–4 retain failures; attempts 5–7 passed compilation.
The check is **compiler evidence only**, not completion of the parent concrete
behavioral matrix. The main fixture, assertions, runner, and result interpretation
belong to the parent integration lane. Leaf-only compile attempt 1 is narrower
than the fourteen-subject compile attempts 2–7.

The bounded compiler command is `python3 verification/android-private-owner-concrete-leaves/compile-leaves.py`.
It resolves the exact roster, strips implicit JVM options, uses the installed
OpenJDK javac with `--release 17 -Xlint:all -Werror -proc:none`, supplies empty
class/source paths, caps execution at 45 seconds and combined output at 1 MiB,
records before/after source hashes, and removes its owned scratch on success or
failure. It does not invoke a shell child, native runtime, capture tool, simulator,
emulator, physical phone, or process inventory. The earlier simple compilation
attempts retain their exact commands and output; their completed compiler scratch
was subsequently removed, as recorded in `cleanup.json`.

## Fixture API

`ConcreteHostProbe.hook` is a nullable `BiConsumer<String,String>`. `hit(method)`
means phase `entry`; `hit(method, phase)` and the receiver-aware overload are the
instrumentation entry points. Each selected native method calls `entry` before
primitive mutation and `beforeReturn` after native work/callbacks. The hook may
reenter actual product methods or throw an unchecked failure. No leaf decides
what that reentry means. Hook failures are not swallowed.

`lastEvent()` exposes `method`, `phase`, `receiver`, `productionClass`,
`productionMethod`, `productionLine`, and `site()`. StackWalker finds the nearest
frame in one of the fourteen actual product classes, retaining nested-class
identity and exact source line. `events()` is a read-only snapshot;
`count(method,phase)` returns invocation count. History is limited to 65,536
entries and 4,096 method/phase keys per reset. `reset()` clears the hook, counters
and history. Hooks should inspect `lastEvent()` before making a reentrant call.

The native method identifiers use simple owning leaf names, for example
`View.setEnabled`, `TextView.setText`, `ViewGroup.addView`,
`UiModeManager.addContrastChangeListener`, `Handler.post`,
`EditText.onCreateInputConnection`, and `BaseInputConnection.commitText`.
Overloads can share a name; the exact reached product source frame and receiver
identify the selected barrier. Intermediate Android helper frames are excluded
from production-site selection.

`Activity.resources`, `.assets`, `.resolver`, `.services`, `.window`, and
`.destroyed` are mutable fixture state. `AssetManager.put(name,bytes)` supplies
fixture-authored descriptor bytes to the actual installed-capture/decoder path.
The asset leaf neither parses nor creates descriptors. A new root is zero-sized
and unattached; use `layout`, `hostAttach(token)`, `hostInsets(insets)`, and
`hostWindowFocus(value)` to deliver primitive state and listener callbacks.
`rootInsets` can be null. `Window.decor` is a normal View whose geometry can be
set by the fixture. Root/parent traversal supplies actual primitive attachment,
window token, focus, location and inset state.

Listener lists and counters retain the exact registered object identities. The
same hook mechanism injects before/after acquisition, uncertain registration,
removal, reentrant notification, and ordinary/fatal failures for each slot.
`Context.hostConfigurationChanged`, `ContentResolver.hostNotify`,
`UiModeManager.hostContrast`, `AccessibilityManager.hostHighContrast`, and the
View host methods explicitly deliver their stored callbacks. `ViewTreeObserver.alive`
models target death. These methods model callbacks; they do not assert platform
scheduling behavior.

`Handler.latest` exposes the most recently constructed Handler. Each Handler has
its own queue, `postCalls`, `removeCalls`, `postResult`, `postFailure`,
`removeFailure`, and `removeEffective`. `snapshot()` preserves runnable identities
for stale-delivery controls. `drainOne()` consumes then synchronously invokes one
queued runnable; `drainAll(limit)` is bounded. `post()` never runs inline. A throw
from the before-return hook may leave an enqueued runnable, deliberately retaining
uncertainty. Removal return never creates a reclamation claim.

View/ViewGroup retain frames, measured extents, hierarchy identities, layout
parameters, visibility, enabled/pressed/focus, scroll, root state, native styling,
listener targets and invalidation counts. All eleven required early virtual
constructor entries are deliberately called before subclass Record assignment.
Native mutation then synchronously invokes applicable layout, focus, visibility,
attachment, checked, text and selection callbacks. Parent interception release
is separately hooked. Canvas retains drawing operations and mutable save/transform
state. Path retains its authored native command sequence. Draw dispatch executes
actual product overrides through ordinary view traversal.

TextView retains editable identity, spans, selection, watchers, filters, settings,
text layout and callbacks. Text layout is a deterministic host approximation
with wrapping, baselines, line widths and size proposals, **not** Android shaping
or raster conformance. EditText counts real host superclass connection acquisition
and retains the base connection. BaseInputConnection models text/composition/
selection/key/editor actions and counts mutating forwarding calls. The actual
product InputConnectionWrapper performs admission. The leaves read no V2 fence,
operation, presentation, observer, or expected result. Clipboard and accessibility
routes invoke ordinary widget behavior and callbacks.

`NativeBridge.reset()` restores counters and fixture-controlled outcomes.
`preparedPacket` is supplied by the parent independently authored packet fixture;
the leaf has no packet schema, decoder, descriptor generator, or authority logic.
`preparedToken` is an opaque nonzero bit pattern, `createResult` defaults to 1,
and `commitStatus`/`abortStatus` default to 0. The Candidate preserves the real JNI
surface's packet cloning. `lastInput` retains the exact caller reference;
`lastPreparedPacket` retains the supplied packet reference; `lastHandle`,
`lastToken`, `lastOperation` and all six engine call counters expose native calls.
Each boundary supports entry/beforeReturn hooks and dedicated failure slots.
The product coordinator owns its own retained packet reference independently.

## Boundaries

No test here establishes Android listener reclamation, main-Looper/native
scheduling fidelity, native text shaping, actual IME behavior, Swift/JNI execution,
public V2 routing, physical-device qualification, OTA publication, FieldLog
qualification, signing/store acceptance or any GA gate. Newly unrun native checks
remain pending under the active pause. No unrelated process or native instance
was queried, started, stopped or modified.
