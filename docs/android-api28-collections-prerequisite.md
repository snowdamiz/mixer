# Android API 28 collection/library prerequisite

**Source/compiler evidence only; root selection and independent review pending.**
The smallest next slice is to accept and retain the exact emitted-library audit,
without changing accepted product code. The installed official D8 already lowers
the reachable newer collection factories to public API28-safe operations. A source
reference to an API30/31 factory is therefore not, by itself, an emitted API28
blocker. This packet does not enable older-SDK rendering or prove Android runtime
behavior. The optional independently authored snapshot prototype is **unselected**.

The starting point is the accepted bounded A native pair, with
[native acceptance](../verification/android-environment-platform-root-review/native-acceptance.json)
SHA-256 `0c15ca808c2f5684d768125674cdfc0bf48bff672193f79fcaaee47726bf2478`.
All 20 current app Java files are frozen in
[source-map.json](../verification/android-api28-collections-prerequisite/source-map.json).
Seventeen are members of the frozen profile4 adapter23 projection; the other
three are V1 descriptor/resolver and instrumentation compiler companions. The
six non-Java adapter members are explicitly distinguished in
[profile-projection.json](../verification/android-api28-collections-prerequisite/profile-projection.json).
They are not Java-library proof. No live CLI, current root metadata or Git state
was read as a custody anchor. The inherited revision `fb4c8f074f1a3e5eb2b1b1a45b44f0fa61a7cc62`
is context only.

## Actual callsites and collection contracts

The [43-call source index](../verification/android-api28-collections-prerequisite/source-factory-index.json)
records exact lines and snippets. Forty-one calls belong to the private V2
subjects; two additional copies belong to the V1 compiler companion. This index
is navigation, not release authorization. The full actual20 closure was compiled,
then its binary DEX member/type IDs and disassembled call edges were audited.

| Source sites | Required contract in the actual consumer |
| --- | --- |
| `AppearanceDescriptorV2`: three `List.copyOf`, three `List.of` | Resource and face sequences are shallow snapshots, reject nulls, preserve declaration order, and keep duplicate elements until the existing resource/font semantic checks reject duplicates. Copies occur after existing bounded parsing; they must not change malformed/canonical/error-code precedence. Literal theme/button iteration preserves light-before-dark and normal/destructive/cancel ordering. |
| `AppearanceGeometryV2`: two copies, eight literal/empty factories | Commands and points preserve exact order, repeated points and element identity. Later source-list/argument-array changes cannot alter a path. Empty geometry remains empty; extent/radius checks still precede path allocation. |
| `AppearanceResolverV2`: nine list copies, one map copy, one empty list | Group rows, gaps, children, resources and plan nodes retain order and shallow identities. The lookup map has no specified iteration order and is only queried by ID; `Plan.node(null)` returns null before map access. Packet admission rejects duplicate IDs before index creation. No new duplicate policy belongs in map copying. |
| `NativeAppearanceViewsV2`: separator copy, empty gaps, empty map | Separator order and snapshot isolation are required. Empty gaps are only iterated. `Group.records` is an empty read-only placeholder later replaced with the real record map; it does not mint identity or readiness. |
| `OwnerLifecycleV2`: ten empty refusal returns, one `batch` copy | Thread checks precede identity/retirement refusal. The accepted state transition and `MAX_DECISIONS <= 5` assertion precede copying. Preserve decision order and exact token/resource object references; callers iterate decisions, never mutate the batch. The list object itself has no identity authority. |
| `AppearanceResolutionV1`: two copies | Preserve the existing V1 baseline and bounded child/node snapshots. These compiler companions are included so a private-source claim does not hide library references retained in the renderer class. |

No actual `Set.of`, `Set.copyOf`, `Map.entry`, `Map.ofEntries` or `Map.Entry.copyOf`
occurs in this frozen closure. Existing mutable `HashSet` membership tables and
`HashMap`/`LinkedHashMap` builders are intentional: their existing validation and
insertion behavior must remain. No finite Set helper is needed.

`UiPacket.Node` deliberately installs `Collections.unmodifiableList(children)`
**before** recursively appending children in `UiPacket.node`. A snapshot there
would erase subtrees. Properties/actions and the packet index likewise use
builder-owned wrappers; raw builders do not escape `decode`. The package-private
constructor itself is not a general defensive-copy API. The host oracle exercises
this actual aliasing behavior. Renderer candidate maps wrap local `LinkedHashMap`
builders after population and preserve deterministic traversal and record identity.
Those wrappers, mutable geometry maps, journals and roster arrays are outside any
replacement proposal. A live wrapper must never replace an existing snapshot.

## Official floors and emitted behavior

Official Android references place `List`/`Set`/`Map.of` at API30 and `copyOf` at
API31. List factories retain sequence order and reject nulls; map factories reject
null keys/values and give no iteration-order guarantee. Set factory duplicates
and copy duplicates have different contracts: factories reject duplicates, while
copying may retain one equal element. These distinctions forbid a generic
all-collections rewrite. [List](https://developer.android.com/reference/java/util/List),
[Map](https://developer.android.com/reference/java/util/Map),
[Set](https://developer.android.com/reference/java/util/Set).

The exact official installed SDK37 API database and a finite excerpt with
transitive declaration ancestry are retained with hashes in
[tool provenance](../verification/android-api28-collections-prerequisite/tool-provenance.json)
and [official-sdk-api-excerpt.xml](../verification/android-api28-collections-prerequisite/official-sdk-api-excerpt.xml).
`Collections` wrappers/empty constants and basic collection operations are public
before API28. `Objects.requireNonNull` is API19; `Double/Float.isFinite` and
`java.util.function.IntConsumer` are API24. Actual renderer `toArray(T[])` is the
API1 overload. The `Collection.toArray(IntFunction)` overload is API33, not the
same method. [Collections](https://developer.android.com/reference/java/util/Collections),
[Collection](https://developer.android.com/reference/java/util/Collection).

Collection streams and Java8 default methods generally begin at API24; that does
not make every later method available. `Stream.toList`, `takeWhile`, `dropWhile`
and `ofNullable` are API34, and `Map.Entry.copyOf` is API35. No stream type or
operation is emitted here. The source/library inventory also finds no reachable
newer `Map.compute/merge/getOrDefault`, `List.sort/replaceAll`, `removeIf`, optional,
`java.time` or newer IO dependency. Modern default methods in the **host oracle**
are mutation controls, not product calls. [Stream](https://developer.android.com/reference/java/util/stream/Stream),
[Map.Entry](https://developer.android.com/reference/java/util/Map.Entry).

JDK25.0.4.1 compiled the actual20 sources as Java17 against SDK37; official
build-tools37.0.0 D8 `9.2.4-dev`, implementation jar SHA-256
`a26ee56252adcff6752c379ae255a0ad538ebec60189e078ec6855487107637d`,
then ran with `--min-api 28 --lib android.jar`. The resulting unsigned DEX has
170 unique referenced Java members and 60 Java types; every one resolves through
official SDK metadata at API28 or earlier. There are zero unknown Java members,
zero stream types and no remaining `java.lang.Record` superclass reference.
Later Android framework/editor classes still exist and remain separately gated
or pending; this is specifically a Java-library result.

The [lowering/call-edge packet](../verification/android-api28-collections-prerequisite/attempt-1/collection-lowering.json)
retains the exact generated bodies and 57 relevant edges:

- `AppearanceDescriptorV2$0.m(Collection)` allocates an owned `ArrayList`, traverses
  the source in order, checks each element for null, and returns an unmodifiable
  wrapper. It does not retain the source collection.
- `$1.m(Object[])` copies checked argument elements into its own list; the one,
  two and three argument helpers forward in argument order. Repeated equal
  elements survive.
- `AppearanceResolverV2$Plan$0.m(Map)` allocates a new `HashMap`, rejects null keys
  and values while traversing entries, then returns an unmodifiable wrapper.
- Empty factories lower to public `Collections.EMPTY_LIST/EMPTY_MAP`. Core batch
  calls the generated copy helper after its size assertion. Records are lowered
  to generated program classes, including `com.android.tools.r8.RecordTag`.

These are inspected **official compiler outputs**, never copied into product
source. They require no newly added core-library dependency/configuration.
Language desugaring and separately configured library desugaring are distinct;
the command and resulting DEX, rather than an assumed setting, support this
specific finding. [D8](https://developer.android.com/tools/d8),
[Java language and API desugaring](https://developer.android.com/studio/write/java8-support).

No exact exception-message, collection-implementation identity, source/JDK
`toArray` versus iterator traversal, or no-op-mutator exception equivalence is
claimed. The separate [empty-mutation witness](../verification/android-api28-collections-prerequisite/empty-mutation-witness/receipt.json)
passes eight JVM assertions: `List.of().clear()` and `.removeIf(false)`, and
`Map.of().clear()` and `.remove(absent)` throw on this JDK; the corresponding
`Collections.emptyList/emptyMap` operations return normally. The DEX uses the
empty constants, so universal Java17 factory exception equivalence is explicitly
**unproved and excluded**. The witness executes the JDK, not API28 or the D8 bodies.

Visibility and consumers bound the proposed acceptance. `OwnerLifecycleV2` and
its list-returning methods are package-private; the only actual product list
consumer is private `NativeOwnerV2.process`, which iterates decisions in order.
No returned decision list is published as a supported Java API. Other code added
to that package could call mutators, so package visibility alone is not proof of
universal exception equivalence. Geometry's two empty constants and the resolver's
empty section gaps feed existing copy constructors before escaping; views'
remaining empty gaps are a local read-only iteration. `Group.records` is a
package-private placeholder in package-private native classes: `installChildren`
replaces it at views line601, while Group only calls `get` and `entrySet`.
Its map is never mutated through the field. A future public list/map API or new
mutating consumer needs a separately selected exception contract and evidence.
Concurrent mutation and hostile caller-supplied collection
implementations are not exposed by these factory callsites. Shallow element,
token and native-record identities remain significant and are preserved.

## Build assumption, fallback and acceptance boundary

The sealed profile4 driver is copied as inert source with its exact identity in
[consumer-build-contract.json](../verification/android-api28-collections-prerequisite/consumer-build-contract.json).
It chooses build-tools37.0.0, SDK37 and JDK25, invokes the same D8 flags, hashes
the complete build-tools distribution including `lib/d8.jar`, and compares the
observed toolchain to the exact local lock before compilation. There is no
observed missing jar hash. A source-profile hash alone is not a D8 identity, and
version metadata alone is not a global approved-binary allowlist. This finite
run clears implicit JVM-option variables; the frozen builder inherits them.
Reproduction assumes those options do not inject or change compilation.
The [consumer-flags receipt](../verification/android-api28-collections-prerequisite/consumer-flags/receipt.json)
also repeats compilation with the sealed driver's exact Java17
`-Xlint:all -Werror -classpath` and D8 flags over the frozen20 sources. Its emitted
170-member/60-type Java reference closure is identical. No generated app, Swift,
JNI, APK, signing or installation step was run.

The generated builder currently does not perform an emitted Java API-floor audit.
The smallest useful follow-on is an independently reviewed finite verification
gate over the exact pinned compiler result. If consumer Java inputs, compiler
distribution or flags change, repeat the audit. Do not infer all future Java
library support from these 170 members or merely from `--min-api 28`.

Only if root separately selects an owned-source alternative should a finite
helper replace the named factories. The unselected
[prototype](../verification/android-api28-collections-prerequisite/prototype/CollectionSnapshotsPrototype.java)
has four operations: checked shallow list copy, checked list literals, checked
map copy and an empty map. Each wrapper owns a new backing collection. No Set,
stream, parser, lifecycle or general desugaring subsystem is proposed. The host
oracle passes 93 assertions on isolation, duplicates/order, element identity,
null refusal, direct/iterator/view/default mutations, original exception identity,
the actual packet builder alias, and actual core thread/decision ordering.
These are JVM tests of an unselected prototype and existing pure sources, not
Android tests or execution of D8 helpers.

A future helper change would touch descriptor, geometry, resolver, views and the
accepted core (and the V1 companion only if separately included). Preserve each
existing callsite position and validation precedence. Do not precompute batches
before transitions, catch/translate allocation or linkage errors, add work between
successful `commitV2` and `finishV2`, change eight-slot observer ownership or fatal
failure precedence, or clone tokens/records. Any changed core/source closure and
future profile selection require root coordination and independent review. No
profile5 bytes, wire/descriptor identity, SDK guard or route is selected here.

Reproduce on a clean packet copy with `python3 verification/android-api28-collections-prerequisite/run.py`,
then `python3 verification/android-api28-collections-prerequisite/audit.py` after
recording official `dexdump -d` as in the retained command. The source-only audit
adds four negative metadata controls. Two failed audit attempts remain recorded:
an incomplete inherited-metadata excerpt and modified-UTF8 disassembly text
decoding; both were corrected without changing the compiled artifact.

Computer use, capture, UI automation, native/simulator/emulator/phone execution
and process inventories were not run. Owned host children were reaped and scratch
removed. Product code, dependencies, root metadata, credentials, publication and
Git were not changed by this lane. API28 native verifier/class-loading/library
runtime, older-SDK visual accessibility/insets/editor/value semantics, public V2,
TalkBack/design parity/final phones, immutable separate-repository FieldLog,
OTA/signing/store/operations and accountable GA remain pending. Both SDK<36
guards remain intact and this packet admits zero new rendering contexts.
