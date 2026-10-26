# Independent private-owner mechanical leaf review

Recommend root admit the exact **leaf 3** snapshot for bounded mechanical test
reuse, with the limits below. No unresolved leaf-only blocker remains. This
review accepts no product implementation. Mutable product source, producer product tests, the
parent implementation evidence and all native/UI/capture/process-discovery paths
remain unopened. The sealed preaccess plan and its 60 members are unchanged.

The review-owned evidence directory is
`verification/android-private-owner-independent-review/leaf-review-1/`.
Leaf 1's manifest is
`f4633dab3fd25713feaf93162b5ffb888b277108683781b7b118a010cf14b79e`:
74 files, 96,681 bytes, exactly 73 selected substitute FQCNs plus test probe.
Every complete body was independently inspected. None mints an owner/core token,
changes a Mixer fence, constructs installed/environment/current authority, or
encodes an expected product decision. `Editable` uses reflection only to allocate
a generic span array. The probe's product-class-name allowlist classifies stack
frames; it neither creates product objects nor grants authority. JNI numeric
handles/tokens remain opaque test data and are distinct from lifecycle tokens.

The source inspection is supported by leaf-only executable controls. All 74
sources compile through official Homebrew **javac 27 targeting Java 17** with
`--release 17 -g -Xlint:all -Werror -proc:none` and empty class/source paths.
The JVM is OpenJDK 27, not Android and not a Java 17 runtime. Leaf 1 passes twelve
controls and eighty assertions. These controls cover probe callback positions and
bounds, non-inline Handler delivery and stale identities, eight listener shapes,
deliberate early virtual entry, simple hierarchy, asset byte streams, synchronous
Editable/TextWatcher order, simple composition/codepoint behavior, all 24 declared
wrapper forwards, JNI counters/copying/fatal identity, and primitive motion/drawing.
No actual product class is compiled or executed; product test count is zero.

## Probe findings and separately admitted deltas

Leaf 1 retains only product class/method/line in each Site. Those triples cannot
distinguish two same-target invocations on one line. The sealed baseline contains
`NativeAppearanceViewsV2:L104:C25:1` and `:L104:C109:3`, both `container.addView`.
This is a limitation of leaf-1 retained traces, not a finding that the unseen
candidate retains that formatting. A synchronous independent hook can capture
descriptor/bytecode index while the actual caller frame remains on stack.

The independent synthetic trace witness demonstrates two Paint.setColor calls
on line 315 at bytecode offsets 3 and 9 under descriptor
`(Landroid/graphics/Paint;)V`. Its class name deliberately matches the probe's
allowlist prefix solely to exercise instrumentation. It is **not** NativeRenderer,
a renderer double, a copied product body, or evidence for any of the fourteen
actual product subjects. The witness's class hash and `javap` output are retained.
Actual candidate evidence must separately bind exact compiled product class hashes,
method descriptors/offsets and the source inventory; class-name filtering alone
cannot establish that a product body ran.

Leaf 2's manifest is
`d58e1c1b8ca942089603c1e5d3a63bec93198935f256e7ab6f92e2b7a31a70f9`:
74 files, 96,764 bytes. All 73 platform/JNI bodies remain exactly identical to
leaf 1; only ConcreteHostProbe changes. It adds Site descriptor and bytecode index,
but its default StackWalker lacks `Option.RETAIN_CLASS_REFERENCE`. Independent
compilation passes, then execution fails with
`UnsupportedOperationException: No access to RETAIN_CLASS_REFERENCE` at probe
line 35 when the first synthetic product-class frame is processed. The failure
occurs inside the probe before the external hook. Leaf 2 is not executable-qualified;
its exact failure, commands, streams and class hashes are retained unchanged.

Leaf 3's manifest is
`d772bfae9febf9106b1338be259cb026e4293d8e287fa792939340754ccdda38`:
74 files, 96,805 bytes. The sole change from leaf 2 is
`StackWalker.getInstance(StackWalker.Option.RETAIN_CLASS_REFERENCE)`; all 73
platform/JNI sources remain byte-identical across all three snapshots. The exact
probe SHA-256 is
`8ce84fed0c4dbc5574fe42c193fa04e0c5cf8e715260b21103fa44f5dd34de75`.
This adds access to JVM frame metadata only, with no product ownership or authority
change. Independent strict Java 17-target compilation and all twelve leaf-only
controls now pass, with eighty-two assertions. The revised retained descriptor
and offsets match the independent hook's offsets 3 and 9 exactly. This resolves
the retained-identity limitation and the missing StackWalker option for this
bounded synthetic control. Leaf 2's rejection remains historical evidence.

This recommendation is limited to the exact leaf-3 bytes. Any further leaf or
probe source delta requires separate review. Root retains reuse selection.

## Mechanical scope and semantic limits

These leaves are suitable only as controlled host boundaries once root admits
the exact reviewed snapshot and probe. Later independent actual-subject tests
remain mandatory. Call-site capability is not 184-site/new-site coverage; every
actual reached ID must be distinct through a strong hook identity or independently
verified candidate source/compiled mapping. The complete seven-case matrix and
five V1 positives remain unchanged.

`semantic-limits.json` records each material limitation. Handler is a manually
drained queue, and `latest` names the last Handler constructed rather than a
particular owner. Looper has explicitly controllable host identities. Listener
notifications run synchronously and do not model framework/executor/binder order.
View constructors deliberately call overrides early; view focus, touch dispatch,
layout scheduling, attachment and coordinates are simplified. Typography is an
estimate, while Canvas/Path record commands without rasterization. Motion stores
one pointer tuple even when a requested index differs.

TextView replacement invokes real leaf before/on/after callbacks before the
delegate returns. This proves that the host leaves can exercise the necessary
synchronous shape; it does not prove the actual product TextWatcher/owner/renderer
successor sequence. Direct Editable edits do not notify TextView, newCursorPosition
is ignored, generic span migration and batch semantics are incomplete, and the
InputConnection interface is a subset. Several content/command delegates expose
only simple status behavior. Actual product retained-connection gating is still
required. Assets supply raw ByteArrayInputStream bytes; JNI exposes fixture packet
data/statuses/counters without Swift, engine, effect or revision semantics.

The probe bounds history at 65,536 events, 4,096 method/phase keys and 24 filtered
frames. Tests must split bounded witnesses or report unreached scope when these
limits are hit. Nested leaf calls may emit events inside one already-entered
opaque call; do not count these as new Mixer mutations. The successful product
commit/finish interval must remain free of added hooks/captures/callback work.

Every command uses at most one owned child, a 120-second wall bound, 256-MiB Java
heap and 2-MiB output caps. Literal argv, tool versions/binary digests, source and
compiled class hashes, bytecode, streams, exits and failures are retained. Owned
children were reaped and exclusive scratch removed after passing and failed runs.
There was no dependency/install, git, CI, production action or unrelated process
change. Native/JNI/physical/accessibility/performance, public V2/OTA, published
separate-repository FieldLog, signing/store/operational and GA qualification remain
pending.
