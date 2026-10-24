# Independent Android appearance V2 data review

Recommendation: accept only the sealed Java V2 descriptor/geometry **host data
slice**. No blocking finding was observed in this scope. Root remains the
accountable acceptance owner. This is not a GA gate or native implementation
acceptance.

The reviewed producer receipt is
`verification/android-appearance-v2-data/candidate-3/receipt.json`, SHA-256
`b8a983fe2510f80b508c211b2fb0eed079ae4f3857261ca6f3207ad01f50896f`.
The producer seal, all producer input copies, logs and local artifact hashes were
checked before review. The input manifest captures current revision/tree plus the
exact observed source closure, including product files that were untracked at
capture; a Git tree alone is not used as their identity. Copies are read-only and
hash-checked before and after execution. Each changed compiled source closure has
its own build target and each Swift optimization mode its own module cache.

## Independently executed evidence

| Review | JVM default | JVM `-Xint` | Swift `-Onone` | Swift `-O` |
| --- | ---: | ---: | ---: | ---: |
| Descriptor cases | 6,165 | 6,165 | 6,165 | 6,165 |
| Accepted, exact typed reconstruction/canonical round trip | 1,055 | 1,055 | 1,055 | 1,055 |
| Rejected | 5,110 | 5,110 | 5,110 | 5,110 |
| Geometry cases | 100,989 | 100,989 | 100,976 | 100,976 |
| Exact parser error/boundary checks | 13 | 13 | — | — |
| Ownership checks | 3 | 3 | — | — |
| Additional complete byte-boundary descriptors | 3 | 3 | 3 | 3 |

The 5,584 descriptor cases from root's independent Swift review (973 accepted /
4,611 rejected) were regenerated against the retained closed schema and semantic
oracle. This corpus is independent of the Java author. This reviewer added 581
cases (82 accepted / 499 rejected): all 256 byte values at an ID position, malformed
numeric tokens, long unsigned numbers, noncanonical/invalid escapes, systematic
truncation, catalog totals/counts and font normal/italic relationships. The separate
byte supplement admits complete descriptors at 65,535 and 65,536 bytes and rejects
65,537 bytes. Its icon catalog is synthetic metadata only.

The independent Java probe traverses every accepted typed field and reconstructs
the canonical descriptor without a product or author-test encoder. Those bytes
must equal the actual input. The separately compiled actual Swift codec must
decode, validate and canonically encode the same input exactly. No Java author's
test entry point is used as independent acceptance. The producer's V1 7,147-case
execution is retained author evidence; this reviewer checked its hash bindings
and cross-format rejection, without claiming a second independently authored V1
regression corpus.

The geometry oracle uses the frozen shape artifact/contract checker with Python
arbitrary-precision integers and a separate exact binary64 rational rounding
calculation. It checks every spacing half-step and every supported density
half-step plus the immediate `nextDown`/`nextUp` neighbor, nonfinite/raw support
limits, extent ceiling, fixed switch points, group clamp transitions/random boxes,
fractional pixel-coordinate bits, absolute pixel-edge rounding and RTL placement.
Thirteen cases exercise the extra Java signed/`long` domain that Swift's unsigned
parameters cannot represent; those do not count as actual Swift calls. Values of
exactly 8,192 versus 8,193 admitted nodes, container levels 20/21, arrays 64/65,
bytes 0/65,537, key sorting, duplicates and non-ASCII have exact Java error checks.

All Java classes compile with JDK 25, `--release 17 -Xlint:all -Werror` and are
checked for class-file major 61. Actual tool outputs, absolute arguments/cwd,
source/copied-input hashes, payload hashes, executable/class hashes and command
results are retained in `candidate-2/acceptance.json` and
`byte-boundaries/receipt.json`. Large binaries/module caches stay ignored under
`build/`; corpus manifests are retained as lossless gzip with both compressed and
raw digests bound by the top-level recommendation.

## Source review observations

- The ASCII grammar rejects non-ASCII before parsing, constrains strings while
  reading, rejects unsupported escape spellings, and admits counts/depth/array
  children before retaining them. Sorted unique keys plus shortest wire tokens
  make successful bytes canonical. The Java `long` parser's narrower range than
  Swift's `UInt64` cannot admit a different descriptor: every schema integer is
  at most 4,194,304 and every derived geometry parameter has its own checked bound.
- Typed admission retains complete supplied app themes, explicit platform mode
  and reason, closed profile metrics, all paints and geometry values. Catalog
  uniqueness/totals, font references and normal-weight coverage, profile/floor
  invariants and clear disabled paints fail closed. No Java default theme or
  implicit platform appearance is supplied.
- Group arithmetic is checked before narrowing and cannot overflow `long` in the
  admitted domain. Fixed switch geometry and authored group coefficients agree
  with the frozen contract and Swift. Comparing the fractional remainder to 0.5
  preserves a value immediately below a half; adding 0.5 first could lose that
  distinction. Pixel products fit exact binary64 integer precision.
- The outer descriptor and nested records hold final immutable values. Input
  bytes, resource/face lists, path commands and command points cannot mutate an
  accepted object through an admitted alias. Shared mode explicitly retains one
  theme for both platforms. Path construction is private to the closed shapes.

## Retained failed review attempt

The initial preflight assumed producer command logs used one `log` field; the
actual receipt has separate `stdout`/`stderr` fields. This was corrected before
source copying or compilation. The first compiled review attempt passed the
descriptor and geometry corpora but its intended value-count fixtures were
accidentally overdeep, producing `depthLimit`. Its failed receipt is
`failed-attempt-1.json`; the original root-level inputs/logs/manifests are retained.
The corrected candidate uses a fresh build closure and all 13 intended parser
checks passed. These were review harness defects; no product changes were made.

## Reproduction and limits

Run `python3 verification/android-appearance-v2-independent-review/review.py candidate-N`
with an unused candidate directory. This freezes a new exact source closure and
executes the complete main review. The exact executed byte supplement script is
retained as `byte-boundaries/byte-boundaries.py`. It uses the retained
`candidate-2/inputs` closure and intentionally refuses existing supplement
output/build directories; reproduce it in a separate directory copy with those
output/build paths absent.
Check the retained current review with:

```sh
python3 verification/android-appearance-v2-independent-review/verify-review.py --with-binaries
```

No Android framework, native adapter/rendering/measurement, installed resource/font
identity or glyph coverage, window/preference/configuration behavior, accessibility,
interaction, JNI/packet/bootstrap integration, signing, OTA authority or health
attachment is accepted here. Physical iOS/Android side-by-side design review under
product-plan §8.3 remains pending. Phones are disconnected; no discovery or run was
attempted. Separate immutable published FieldLog packages and all compiler, store,
customer, operational and GA gates remain pending.
