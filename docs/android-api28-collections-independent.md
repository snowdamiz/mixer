# Independent Android API28 collection review

Accept the exact frozen Java-library API-floor evidence and the existing private
read-only consumer scope, subject to root selection. No collection replacement is
needed for this emitted artifact. This does not accept universal Java factory
exception equivalence, API28 class loading or execution, additional rendering
contexts, public V2, or a new source profile.

The producer manifest SHA256 is
`168ade73aa770bf1d3c6c595b3c24b55f3ed99dcba400d4422694b60c6749c0c`.
The independent review verifies all 95 members / 15,196,628 bytes. Profile4 manifest
`046f1a5a4f69dae7dafb529d55caf7fcd475a54614c40103f90be1d7fd6d39b4`
binds the reviewed source-map and all 23 adapter snapshot members. Seventeen are
Java and six are non-Java; the latter are custody checks, not library/runtime
proof. The Java compiler closure contains those 17 files plus the V1 descriptor,
V1 resolver and instrumentation companions. All 20 current canonical Java files
match the frozen source hashes before and after the run. The inherited revision
`fb4c8f074f1a3e5eb2b1b1a45b44f0fa61a7cc62` is context, not live Git custody.

Run `python3 verification/android-api28-collections-independent/review.py` from
the repository root to reproduce the bounded checks. It imports no producer
runner or audit. The retained receipt reports **851 checks**, seven independent
negative controls, a fresh exact-flags Java20/D8 compile, 57 fresh pure-source
host assertions, and eight separately counted JDK empty-mutator differences.
The producer's 93 prototype assertions and four negative controls are historical
producer evidence and receive no fresh independent test credit here. The optional
collection helper prototype remains unselected and was neither compiled nor run.

The independent binary reader validates DEX039 magic, header bounds, SHA1 and Adler
checksums, header/map ID counts, MUTF8 string lengths, every global type/prototype/
method/field ID, and every encoded class method. It decodes all **2,307 code
bodies** across 335 class definitions, rejects unknown/reserved opcodes, handles
the three payload formats, and checks instruction bounds. This exact artifact has
no call-site or method-handle table; either would require expanded review. Global
IDs provide the reference census, so it is not restricted to textual disassembly
matches or a selected reachable method. Array types are normalized to their
component classes: 64 Java type descriptors yield 60 distinct Java classes.
The format and instructions are based on the official
[DEX specification](https://source.android.com/docs/core/runtime/dex-format) and
[Dalvik bytecode specification](https://source.android.com/docs/core/runtime/dalvik-bytecode).

All **163 Java method IDs and seven field IDs** independently match the producer's
170-member closure. The review resolves full method descriptors through the exact
official SDK37 API database, accounting for class/member floors, transitive
extends/implements edge floors and removal levels. Thirty-five references require
an inherited declaration. Exact member signatures, including all seven field
descriptors and their declaration owners, are also checked against SDK37
`android.jar` class files. Every Java type and member admits an API28-or-earlier
path; the highest observed floor is API24. There is no emitted Java Record or
stream type. This latest-SDK metadata/signature evidence does not execute Android
or prove API28 native linker behavior. Android framework, Swift and JNI references
are outside this Java-library floor conclusion.

The seven fresh negative controls reject actual `List.copyOf` and the distinct
`Collection.toArray(IntFunction)` overload as post28, reject unknown method/field
names, reject a synthetic inherited member behind an API29 ancestry edge, and
reject truncated or checksum-corrupted DEX. The frozen official excerpt is
checked against the full installed official database, whose hash matches the
producer provenance.

All **57 lowering edges** are independently decoded from binary instructions,
including **15 empty constants**. Each of the eight retained helper/boundary
disassemblies matches the binary instruction code units exactly. Manual operand
and branch review supports these finite contracts:

- The collection helper allocates an `ArrayList` (PC0), obtains source size and
  iterator, traverses in iterator order, applies `requireNonNull` to each element
  (PC23), adds the same reference to the new list (PC27), and returns a wrapper
  over that list (PC31). It neither retains the source collection nor deduplicates.
- The array helper creates a new list, advances indices from zero by one, checks
  each argument and wraps its owned list. The one/two/three argument forwarding
  helpers construct their array in argument order. Argument-array mutation cannot
  change the returned list; element identities remain shallow.
- The map helper allocates a `HashMap` (PC0), traverses source entries, checks each
  key and value (PC33/41), inserts those same references (PC45), then wraps the
  owned map (PC49). No map iteration order or policy for hostile map implementations
  is added. Packet admission already rejects duplicate IDs.
- `OwnerLifecycleV2.batch` checks list size against five and branches to the
  assertion path (PC5) before invoking the copy helper (PC7). The frozen source
  keeps state transitions before `batch`; thread checks precede public refusal
  paths. No work was inserted around commit/finish or any lifecycle operation.

This is a review of compiler output, not Android execution of those synthetic
helpers. The host tests execute the frozen pure Java geometry, packet and owner
sources on JDK25. They verify snapshot order/repeated element identities/null
refusal, nested packet child preservation and unmodifiable wrappers, thread-error
identity before refusal, decision order, token/resource identity, immutable earlier
batches and terminal state. They do not stand in for D8 helper or API28 execution.

The 43 source factory sites comprise 41 private V2 sites and two V1 copies; the
index is navigation only. Descriptor copies follow existing bounded parsing, and
the light/dark and normal/destructive/cancel literal order remains intact.
Geometry point/command copies, resolver row/gap/child/resource/node copies and
views separator copies retain their existing call positions. The lookup map is
private and queried by ID; null is checked before lookup. No `Set.of/copyOf`,
stream operation, newer collection default method, `Optional`, `java.time`, or
newer IO dependency appears in the emitted closure. Existing mutable builders and
unmodifiable live wrappers are left intact.

The 15 empty edges have distinct consumers:

| Edges | Source and consumer scope |
| --- | --- |
| 10 | Core refusal returns. `OwnerLifecycleV2` and its methods are package-private. Binary calls outside the core belong only to `NativeOwnerV2` and its nested `Work`. Source review traces their lists into private `process` (line262), which iterates decisions without mutating or publishing the list. Another future caller in that package could mutate it; this is not a supported public collection API. |
| 2 | Geometry `close` and zero-extent `group` feed `Command` and `Path` copy constructors. The empty constant itself is not exposed by those constructors. |
| 1 | Resolver grouped-section empty gaps feed the `SectionRecipe` copy constructor before use. |
| 1 | Views fallback gaps are a local empty sequence used for iteration/size/get during measurement. |
| 1 | `Group.records` starts as an empty placeholder and is queried through `get`/`entrySet`, without mutation through the map field. |

The independent trace adds a detail absent from the producer's prose: there are
**three** `Group.records` field writes, not just construction and installation.
Construction installs the empty map (views line626); `installChildren` replaces it
with the real map (line601); `NativeRenderer.restoreV2` restores `c.baseRecords`
during rollback (renderer line441) before the following old-root layout. Replacing
the field is not a mutator call on the empty map. Binary field access and external
core-list call evidence is retained in `consumer-binary-ownership.json`.

`UiPacket.Node` intentionally wraps the children builder before recursion fills
it. The fresh nested packet test checks that children and grandchildren survive
and have the same objects as the packet index. Replacing this live wrapper with
a snapshot would remove subtrees. Package-private direct constructors are not
general defensive-copy APIs, and neither constructor visibility nor future
arbitrary callers are covered by the observed-consumer claim.

The separate eight-assertion witness confirms that on this JDK `List.of().clear`
and `removeIf(false)`, and `Map.of().clear` and `remove(absent)`, throw, while
`Collections.emptyList/emptyMap` return normally. Since D8 emits `EMPTY_LIST` and
`EMPTY_MAP`, universal Java17 factory/no-op-mutator exception equivalence is
excluded. Exception text, implementation identity, hostile/concurrent collection
traversal, and deep element immutability are also excluded.

The exact profile4 builder pins build-tools37.0.0 and SDK37 paths, defaults to
JDK25 and verifies JDK25 version metadata, hashes the complete build-tools/JDK
distributions, then compares the observed toolchain to the local lock before
compilation. A local lock is not a global approved-binary allowlist. Only its
reviewed pure `digest`/`tree` functions were extracted and exercised against an
owned fake distribution: changing `lib/d8.jar` changes the hash, symlink target
bytes participate, and an escaping directory symlink is refused. The full driver,
its inspect/build paths and generated consumer were not executed.

Fresh compilation uses Java17 `-Xlint:all -Werror -classpath android.jar` and
official D8 `--min-api 28 --lib android.jar`, with no added library configuration.
It reproduces the producer's consumer-flags DEX byte for byte. The D8 implementation
jar hash is `a26ee56252adcff6752c379ae255a0ad538ebec60189e078ec6855487107637d`;
tool versions, input identities, commands, exit codes and outputs are retained.
The test clears JVM option injection variables; the frozen builder inherits them,
so equivalent reproduction assumes those options do not alter compilation.
[D8 documentation](https://developer.android.com/tools/d8) describes the flags;
the actual output supports this finite lowering result. Changed inputs, compiler
distribution or flags require a new emitted audit. The generated builder has no
automatic emitted API-floor gate today.

Three expanded reviewer assertions initially failed and remain preserved:
an outer-class-only matcher omitted `NativeOwnerV2$Work`; a custody check omitted
the profile's `engine/` packaging prefix for its two Swift members; and an
assumption of only two `Group.records` writes exposed the rollback replacement.
These were review-harness corrections; product and frozen producer bytes did not
change. The final expanded run passes all 851 checks.

No product code, canonical CLI, profile, root metadata, dependencies or Git was
changed. No UI, capture, simulator/emulator/phone, process inventory, generated
app, Swift/JNI build, APK packaging, signing, installation or publication ran.
Eight owned host children were reaped and owned scratch was removed. Both SDK<36
guards remain unchanged. Native API28 verification/class loading/library behavior,
older rendering/accessibility/editor/insets/value semantics, public V2, TalkBack,
design parity/final phones, immutable separate-repository FieldLog packages,
OTA/signing/store/operations and accountable GA remain pending.
