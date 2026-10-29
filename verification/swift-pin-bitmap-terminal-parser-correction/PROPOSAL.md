# Terminal evidence parser correction

This packet proposes only the `test_evidence` correction after failed hosted run
40824584975, head `1eec8e0fc270c0409c8920ee22fd2374f3bd249f`, tree
`f20be7de5a047f1983931961cc3d774e56de80a3`. The retained Debug command exited 0
after 402.217857 seconds. Its 37 summaries report 699 passed and zero failed,
ignored, measured or filtered tests. The original parser rejects the output
because its single-token matcher finds 682 terminals: it misses 11 spaced
compile-fail doctest names and six serialized split terminals. Release never
started. This proposal preserves that original rejection and failed host status.

`parser_function.py` is the exact replacement function, also embedded verbatim
in the proposed full `admit.py`. `admit.py.diff` and `source-scope.json` bind the
old and new source/AST hashes. Every top-level AST node outside `test_evidence`
is unchanged; `bounded_commands.py` is byte-identical. No workflow, canonical
VM, source closure, formatter/linter, argv, Node policy, runtime/output bound,
custody, postflight or cleanup function changes are proposed here.

The parser binds each header and terminal to a `running N test(s)` group and one
strict summary. Group running/terminal/passed counts must agree; the total must
remain exactly 699 with zero other counts, and all nine exact Node oracle names
must occur once. Duplicate identities, unfinished or overlapping headers,
orphan results, malformed/non-ok summaries and count mismatches refuse. Ordinary
identities are ASCII qualified Rust identifiers; doctests use a canonical
relative `.rs` path, qualified item, positive line number and optional
` - compile fail`. Unsupported output shapes fail closed for this frozen profile.

Only the six existing `shared_control_*` identities can open a split result,
using the exact `control_observer serialized lane` marker. Their direct trace
lines must match the observed Rust Debug envelopes. Warm and validation-ceiling
records are restricted to their emitting tests. At least one control trace and a
single standalone `ok` must close the pending header. Trace text cannot create a
new header, running group, captured-output phase or summary. Captured
`--show-output` payload begins only after all group terminals; ordinary panic
messages such as `test mailbox poison` remain payload, while terminal-shaped
headers and summary-shaped lines there refuse. Trace envelopes bind parsing;
they do not independently prove guest numeric semantics or provenance.

The result interface is unchanged: `summaries`, `terminals`, `passed`, `ignored`,
`nodeOracles`, and `scope`. `terminals` now includes complete spaced doctest names
and reconstructed split `(name, 'ok')` pairs. Actual libtest running groups are
required; old synthetic acceptance fixtures containing only terminal lines and
a summary must acquire matching running headers. The original 43 controls remain
frozen with their actual hosted pass. This packet adds 81 focused controls.

Guarded pure Python replay accepts the exact retained Debug stdout (3,262,384
bytes; SHA256 `a6fac84a9d0db5d198a8d479d08b48ed216486a050fe4d7298b53db5daa4e59c`)
as 699 terminals in 37 groups. The 81 controls pass: 53 corrupted-actual refusals,
10 focused grammar positives, 13 grammar refusals, and five guard/scope/original
refusal/actual replay/nonzero-exit checks. The unchanged command helper refuses
a mocked exit 101 before parser admission. `test_evidence(text)` still receives
only text; actual command exit policy remains enforced by the unchanged caller.

Two failed draft replays are retained locally. The first exposed captured panic
payload handling and a relative-dirfd mock-fixture cleanup refusal; the second
exposed source-emitted `control_validation_ceiling` records. The guard blocked
the cleanup attempt before effects outside this packet; no real nested child,
session, group, signal, wait, timer or socket call occurred. The inert mock
fixture was retained under `local/setup-remnants/`, and final scratch is empty.
The later passing draft and final 81-control replay are also retained. Raw and
replay outputs are ignored by this packet's `.gitignore`; only lean source,
controls, diff, receipt and seal are exportable.

The bootstrap installs effect-denying audit hooks and mocks before subject
imports. Only pure parser/source checks and in-memory command mocks ran; no
Rust, Swift, Elixir, compiler, product or Node oracle runtime ran. No Git,
network, held-process probing, native/UI/capture, phone, release/tag, SDK-repo,
global or canonical changes occurred. Physical-device, paused native runtime,
published-package FieldLog, customer/store and GA evidence remains pending.

This packet grants no execution authority. Root may independently accept and
bind the corrected parser into a separately selected Release-only completion
proposal so the already successful Debug command need not repeat.
