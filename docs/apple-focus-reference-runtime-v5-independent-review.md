# Independent host review of Apple reference runtime V5

Conclusion: **rejected for fresh native selection**. The four V4 repair areas
pass the retained replay and finite independent controls. One additional concrete
V5 output namespace defect remains. No producer file was changed.

V5-001 blocks fresh V5 selection: frozen
[`prepare.py:187`](../verification/apple-focus-reference-runtime-v5/prepare.py#L187)
creates `native-run-v4-<run UUID>`, and the actual selected
[`adapter.py:22`](../verification/apple-focus-reference-runtime-v5/adapter.py#L22)
requires that V4 prefix. The selected archive's `join_support.py:248` contains
the same check. The frozen packet and document require `native-run-v5-`.
An actual host `configure_root`/`select_command` probe accepts the schema 5 and
V5 simulator identity, rejects the V5 output directory before calling the
original selector, and accepts the equivalent synthetic V4 directory. The
original selector is replaced with a recorder; no native command is possible.
The [finding receipt](../verification/apple-focus-reference-runtime-v5-independent-review/attempt-2/independent-adversaries/namespace-finding.json)
preserves both outcomes and the dispatch expression. Correction must retain
the V5 namespace consistently and receive a separate frozen review; this review
does not authorize dispatch or alter the frozen V5 producer packet.

Before loading producer code, independent `pathlib`, `stat` and SHA-256 checks
verified all **4,673** handoff members, exact byte lengths and modes. The complete
closure was checked again after both attempts. The exact producer identities are:

| Artifact | SHA-256 |
|---|---|
| Handoff | `3d22fa59106d6bc6c585ed53d720b31f1bbe50f8e811cf528758b274918ac02b` |
| Packet | `86c7d9604c11349fcf46fb35117130f7262f87acb54da533205a32dfc54ae7ac` |
| Producer host receipt | `5a7ee1ce3fdd3919db239ce96775f9f604a3c5108e4f8e932869d1cacf017a73` |
| Reused closed packet archive | `6e5f6d68e3e529b3975e9b11dc6a0baf873c7508393c7c3ff56c28b4149370a6` |
| Immutable 2,393-file input archive | `3b509aadf2b31314ec9fd910acb4fe3b3040505a446fff8f691bf765a599da7e` |

Python **3.14.8** ran the retained controls once in a freshly extracted,
hash-verified 2,418-member closed source/input/tool packet. A separate audit
guard installed before producer imports denies live-workspace reads and scans,
network and native process actions. The producer additionally pins its four
permitted Python composition programs and installs its child guard before
composition imports. The independent controls demonstrate denied live AGENTS,
Settings journal and journal-directory access. All fixture reads therefore come
from the isolated immutable input tree.

| Retained control set | Observed result |
|---|---|
| Original producer | 111/111 |
| Original repair | 25/25 |
| Exact V3 review | 37/37 |
| V4 precision | 19/19 |
| Frozen actual-adapter precision | 8/8 |
| Historical exact review | **32/33**, unchanged malformed direct-TransactionStore fixture failure |
| Frozen V4 independent review | 36/36 |
| Focused V5 repair | 16/16 |
| New independent controls | 19/19 |

The new controls contain **23 actual adapter attempts and 18 actual derived
summary calls**, with synthetic tool returns and observations. They check 142
exact rational scalar timestamps, 124 genuine subnanosecond scalars, canonical
whole-minute offset equivalence including `-04:00`, lexical rejection before
datetime parsing, calendar validity, microsecond freshness endpoints and exact
nanosecond ordering/window endpoints. No rounding, tolerance or budget expansion
is introduced. The caller's full Decimal context remains unchanged across 88
successful and 132 rejected raw documents, under clear, individually set and
fully set flags with every trap enabled and disabled. Actual adapter success
and rejection also preserve hostile Decimal contexts.

Eight incomplete/no-capture/cleanup summary paths remain in the schema 5
namespace; schema 3/4 and old simulator names reject before fixture writes.
The 276 Settings journal files match their independently bound supplemental
archive byte for byte: 1,190,150 bytes, tree
`c5c19c9aa0520f92f904f698823a90994e89166f3693df07ced052e9e38aeb68`.
Missing, changed and unlisted fixtures fail closed and are restored. Exactly
`importer.py` and `join_support.py` differ from the V4 selected source archive;
the other 29 selected files match. The regenerated selected runtime tree matches
the frozen V5 source manifest exactly:
`e039c50a6d297930cb7faf4370aaa4755b9d4ec0abd3ee34637b793d6355dfb9`.
Original native source/product identities, oracle bytes and action/timing
contracts remain unchanged. The inherited revision label
`ba9ad4372f94463ba4d363cdfd76dd565c96413f` is metadata only; exact closure hashes
define the reviewed source. No Git query was performed.

The independently checked V4 replay control class differs only by explicit
namespace/path substitutions. The helper diff contains only storage of an
actually raised canonical-root `ValueError` and re-raising that same object
inside the old capture rejection boundary. Two real early root rejections are
recorded, with timestamp data unchanged. Schema, name and calendar errors remain
early. No exception is fabricated, assertions are retained, and production
validation is not deferred. The [output checks](../verification/apple-focus-reference-runtime-v5-independent-review/post-review-output-checks.json)
also verify every one of the 1,552 newly generated replay output members.

The first authored independent harness attempt is preserved at 13/19: it
incorrectly required one schema label instead of both valid `.5` report labels,
placed a premise after the public-before attachment, and treated tar directories
as files. Its complete source snapshot, logs and outcomes remain immutable.
Attempt 2 corrects these harness mistakes, binds the supplemental archive
directly and passes 19/19. It reuses the already successful retained replay;
historical packets are referenced by exact hashes rather than recopied.

Commands and their stdout, stderr, Python identity, source snapshots and cleanup
are bound by the [attempt 1 receipt](../verification/apple-focus-reference-runtime-v5-independent-review/attempt-1/receipt.json),
[attempt 2 receipt](../verification/apple-focus-reference-runtime-v5-independent-review/attempt-2/receipt.json)
and final review handoff. Attempt 2 receipt SHA-256 is
`83236af0b4a0ab2f5eda2f2c535146285d5e5961219d1498806505179e1de7c0`.
The replay output archive contains only this review's fresh outputs and is
1,303,535 bytes. Reproduce with a fresh attempt number:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v5-independent-review/run_review.py --attempt 3
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v5-independent-review/check_outputs.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v5-independent-review/freeze.py verify
```

Every owned isolated scratch tree is absent after each attempt; both complete
producer closure checks match. No native commands, device/simulator queries,
compiler runs, UI, screenshots, services, network/provider actions, Git mutations
or shared tracking edits occurred. Excluded hosted catalog/authority and
interrupted worker-review lanes were not read, imported or executed. Physical
phones remain disconnected and deferred. Runtime selection, native execution,
keyboard/carrier completion, published FieldLog dogfood packages, signing,
store, operational and GA acceptance remain uncredited.
