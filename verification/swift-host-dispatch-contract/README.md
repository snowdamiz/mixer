# Uncalled Swift host contract packet

Read `../../docs/swift-host-dispatch-contract.md` and `receipt.json` first.
The original VM stays unchanged. `proposal.rs` is appended to an isolated
125-file source snapshot for compiler/borrow/MIR feasibility only. No guest or
WASI operation is invoked. Metadata programs/tests only print actual layouts.

`probe.py setup`, `probe.py check`, `probe.py mir`, `inventory.py`,
`metadata.py`, `probe.py negative negative-final`, and `identity.py` reproduce
the source-bound compiler analysis in a new uniquely owned scratch directory.
The setup command verifies the exact declared baseline closure before use.
`finish.py` verifies artifacts, records limitations, checks live open holders,
and removes only its own scratch after all source snapshots are archived.
It never touches another lane or native test instance.

All runtime acceptance groups H01-H16 are pending. `candidate.patch` is an
uncalled probe module, not an authorized runtime integration patch. The
positive inventory is an additive proposed bound; no live reservation formula
is modified. Current acceptance is solely contract/compiler feasibility.

Historical artifacts are retained: the initial equivalent closure-based
argument/PC witness, its compiler checks, and three metadata generator spelling
failures. Those failures concerned private/public MIR type paths; final
metadata uses the identical public Rust re-export type and passes. A separate
early inventory source scanner accidentally included six ordinary struct-literal
fields outside the memory accounting region; the corrected identity analysis
selects the exact accounting region and reproduces 4,800 unchanged rows.
