# Apple reference runtime V5 output-prefix correction

V5-001 is corrected in a separate host-prepared derivative. The frozen original
V5 packet remains unchanged. This derivative is **pending independent root review
and fresh root selection**; it grants no native or GA acceptance.

The [three-line patch](../verification/apple-focus-reference-runtime-v5-namespace-correction/correction.patch)
changes `native-run-v4-` to `native-run-v5-` at the actual dispatcher output
expression, the packet-local `adapter.py` workspace check, and the selected
runtime archive's `join_support.py` workspace check. The retained `_dispatch`
body otherwise matches the frozen V5 `dispatch` body exactly. The wrapper stages
two product data inputs from the existing immutable V5 input archive and calls
that retained dispatcher. No prior packet closure is reconstructed or recopied.

The selected archive contains 31 files. Only `join_support.py` changes, by one
ASCII byte; its corrected adapter suffix matches the local corrected adapter.
The other 30 selected files retain their exact original bytes. In particular,
the selected and local importer remains the same 28,916-byte V5 implementation,
SHA-256 `592a5063cbdac739a9ca09df4cf4b8e89469e3b370b14920e95ae4074159aae3`.
Previously accepted arithmetic and Decimal-context behavior therefore remains
the exact reviewed implementation; its historical broad tests were not rerun.
The selection template, oracle sources, native product bytes, action sequence,
timing contracts, windows and budgets remain exact frozen inputs. Schema, root
selection and simulator identity remain V5; this is not a V6 namespace bump.

The derivative references the original V5 handoff
`3d22fa59106d6bc6c585ed53d720b31f1bbe50f8e811cf528758b274918ac02b`, original
packet `86c7d9604c11349fcf46fb35117130f7262f87acb54da533205a32dfc54ae7ac`,
independent V5 handoff
`de3a06f28e3e8cc2b1ee0773c50f3181331e5ae05518de60f79a57b33f22c156`, and
the root's [rejection/correction decision](../verification/apple-focus-reference-runtime-v5-root-review/independent-decision.json).
Its verifier checks the 13 directly used frozen references, including the
18,648,051-byte immutable input archive, whose SHA-256 is
`3b509aadf2b31314ec9fd910acb4fe3b3040505a446fff8f691bf765a599da7e`.
The root's earlier 4,673-member and 33-member closure checks remain earlier
evidence; this narrow correction does not claim to rerun those full checks.

| Corrected artifact | SHA-256 |
|---|---|
| Correction packet | `6c57bc5552a4f7e0e21ff1fdd589b270aa98b483f366f78bd88de2e26c0fd7dc` |
| Selected runtime archive | `a526e25ebe8c5ce382a86376afb6076e984c7f92d77c05ae82e7ced54b5f32ad` |
| Selected runtime manifest | `7772b0ed83cdc1d45d3614916bf765d9fc31bb7610126278f6e391f1a776f530` |
| Selected runtime file tree | `8f6c2d184964d88df9fc29352f52bc78644b68f23d7538925e567f6247c1bf0c` |
| Successful host-control receipt | `17825f54c97e667d21c890d3fa751a8766b158c27d81ab34283d6566800bb258` |

Python 3.14.8 passed **13/13** bounded host tests on attempt 2. Five retained
test methods are replayed byte for byte from the frozen V5 test source: selected
module compilation, fresh root/packet validation, archive corruption rejection,
actual adapter configuration/one-shot capture rejection, and unreviewed dispatch
rejection. Their original broad fixture setup is replaced by the minimal
selected-archive setup needed for these five methods; their assertions and method
bodies are unchanged. Eight targeted controls check the exact three-line
derivation, actual selection, path/command rejection, schema/name rejection,
dispatcher agreement, selection hash binding and the host read boundary.

The [selector probes](../verification/apple-focus-reference-runtime-v5-namespace-correction/attempt-2/selector-probes.json)
contain 12 actual adapter selection attempts, including one deliberately
unconfigured attempt. Both the selected archive module and local adapter copy
accept the canonical V5 path and call the substituted original selector exactly
once; V4, V3 and V6 paths reject before that recorder is called. Wrong command,
existing result bundle and redirected workspace controls also reject before
the recorder. Six actual root configuration attempts reject other schema/name
versions. The receipt's `actualConfiguredSelectorProbes` counter counts all 12
selection attempts; [control accounting](../verification/apple-focus-reference-runtime-v5-namespace-correction/control-accounting.json)
records the deliberately unconfigured exception explicitly.

The [dispatch probe](../verification/apple-focus-reference-runtime-v5-namespace-correction/attempt-2/dispatch-probes.json)
calls the real dispatcher with a synthetic, schema-5 root selection. It stages
the unchanged 55-file native product manifest and corrected selected source
archive, imports the actual selected composition under its source/origin guards,
and replaces `h.run` before invocation. That recorder calls the actual configured
selected adapter with its original selector also replaced by a recorder. Its
accepted session is under the dispatcher's `native-run-v5-<run UUID>` output.
Product/source byte verification passes. A second dispatch with the same UUID
rejects before composition, and changed selection bytes reject by the supplied
hash. These are host packaging/routing controls; no native runner is called.

The first attempt is preserved with its source, packet, unittest log, exception
and residual-file manifest. Its five retained controls pass, but the initial
read guard misresolved `shutil.rmtree` child opens that use `dir_fd`; 20 subtest
and method errors were recorded across the 13 methods, and final cleanup also
raised. One harness repair recognizes only the pinned stdlib deletion function's
relative-open event, uses that frame's absolute path, and applies the same read
boundary. The initial packet and source remain under `attempt-1/pre-fix-snapshot/`.
The corrected packet changes only the host harness binding; its selected runtime
archive is unchanged. A separate, bounded cleanup removed all failed-run owned
scratch after recording its file hashes. Attempt 2 then passes without a skip.

The host audit guard is installed before any selected producer import. It denies
all subprocess/native process launches, socket bind/connect/resolution, excluded
lanes, and live reads/scans outside the correction directory, directly bound
original artifacts and Python installation. The controls demonstrate denied live
AGENTS and Settings capture-directory access. Original references and the
correction packet compare equal after the successful run. All owned module,
source, product-input and synthetic run scratch is absent; cleanup receipts and
the small synthetic dispatch output are retained. No simulator or device was
created or queried, and no other project's process or data was touched.

The executed preparation and control commands, tool identity, source hashes and
output are recorded in `preparation-receipt.json`,
`attempt-1/pre-fix-snapshot/preparation-receipt.json`, the attempt logs and
`attempt-2/receipt.json`. The compact [handoff](../verification/apple-focus-reference-runtime-v5-namespace-correction/handoff.json)
binds this document, both attempts and every correction artifact. Verification
without dispatch is:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v5-namespace-correction/prepare.py verify
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v5-namespace-correction/freeze.py verify
```

After independent review, root can separately invoke the correction's
`prepare.py dispatch` entry with `--reviewed-packet` set to the correction packet
hash above, `--root-selection` pointing to one new out-of-band schema-5 selection,
and `--root-selection-sha256` matching that selection. Its `packetSHA256` must
bind this correction packet. The original compile source identity remains
`696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a` and native
product archive identity remains
`0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`.
The tool, simulator identity, ownership baseline and five-minute selection
freshness checks are unchanged. This document and the preparation are not an
authorization to dispatch.

No native execution, compiler run, UI, screenshot, simulator/device query,
service, network/provider action, credential operation, Git operation,
dependency change or shared tracker edit occurred. Excluded hosted
catalog/authority and interrupted outbound-worker lanes were not read, imported
or executed. Physical phones remain disconnected and deferred. Fresh native
execution, keyboard/carrier completion, immutable published FieldLog dogfood
packages, signing, store, operational qualification and GA acceptance remain
uncredited.
