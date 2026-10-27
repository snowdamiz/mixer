# Scoped immutable fixture binding source candidate

This isolated candidate removes the forced `'static` lifetime from fixture
paths, identity preimages, immutable binding owners, and the affine outer
request. A shared `'p0` borrow now ties each view to its existing owner. A local
owned `PreexistingImmutableBindingV1<'p0>` can be borrowed for the entire
consuming call without leaking storage. The result remains owned and has no
borrowed fixture fields. All selected binding/account/quote routes remain their
original pending refusals. This packet adds no operational provider,
constructor, host grant, retry route, executable closure, or publication.

The binding product plan is unchanged. Only the 146-member copied source tree
under this packet is proposed. Canonical source, frozen accepted evidence,
other active lanes, Git state, product status, and gates were not edited.

The accepted source tree is
`27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3`.
The candidate source tree is
`69068367d2eaf334d6881a624cac9142a0b4ecfeed50f23382724ae29e51d5e7`.
All 146 source members were read through the frozen producer's explicit custody
list and checked against its manifest. The producer custody profile row points
to an older profile, so this packet substitutes only the explicitly accepted
outer-parent overlay profile, verifies its SHA
`b19bca0a2f5ad193fc782061a2f345bd75b9414408643823b8f7691c89bc150f`,
and records that effective origin in `accepted-source-custody.json`.
`source-delta.patch` and `exact-edits.json` contain the complete lifetime/comment
delta; 145 other member bytes are identical. The frozen origin revision
`975b2e3ef25255a882e7476780caa2e844ce928d` in compiler receipts describes the
accepted input provenance, not a fresh live Git query.

Exactly two predeclared compiler processes ran with the accepted production cfg,
target, compiler options and environment, rebased only to owned scratch paths.
The exact rustc executable is
`/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc`,
SHA `dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0`.
The retained executable-bound version is rustc 1.99.0 (b940084d7 2026-09-28),
LLVM 23.1.1, host/target aarch64-apple-darwin. No new version process ran.
Both plans preceded their invocations and set a 55-second child deadline plus
bounded exact process-group cleanup. There was no compiler retry, test cfg,
code generation, binary execution, product run, device run, or UI/capture.

- Positive production metadata plus MIR: exit 0 in 3.32 seconds. The inert local
  owner probe accepts an owned immutable binding, borrows its local value,
  constructs the private request, and consumes it. It is never selected/called.
- Combined negative production metadata: exit 1 in 3.03 seconds, with exactly
  E0515 twice, E0506, E0505, and E0382, in that order. The probes reject a request
  escaping its local binding, a static identity escaping a stack array,
  mutation under a live shared identity, dropping a Vec under that live borrow,
  and consuming the non-Copy request twice. Full actual diagnostics are retained.
- Eight pure-host source/evidence/adversarial-comparator tests passed. These
  Python checks execute no product or Rust test binary. They check reproducible
  source custody, inert tail manifests, unchanged selector/function bodies,
  actual terminal/cleanup receipts, the full MIR/layout result, and comparator
  sensitivity to semantic/constant/allocation/relocation changes.

The full positive MIR is retained as deterministic `query.mir.gz`. All 2,020
actual production function bodies and 248 const/static/anonymous-constant
bodies compare exactly to the frozen accepted full MIR after narrowly scoped
display normalization. All 1,953 allocation blocks also match, including raw
bytes, extents, alignments and mapped relocation targets. A bijection derived
from paired allocation headers accounts for rustc's allocation ID renumbering;
header ordinal or the observed +4 offset alone does not pass. Only the six
reviewed types' added anonymous lifetime parameters and the newly generic
`selected_outer_request_v1` lifetime argument are erased. Literal strings,
operation constants, places, moves, calls, CFG and drop paths are preserved.
Exact scratch prefixes, displayed impl coordinates, and rustc display comments
outside literal strings are also normalized. Four named inert diagnostic/probe
functions and their anonymous layout constants are excluded. No production
function is excluded. The first two offline text-comparison failures and their
reviewer preimages remain under `attempts/`; neither required source changes or
compiler reruns. The initial custody-helper introspection error is also retained.

All 44 accepted concrete inline layout observations match. The additional
`Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>` size/alignment are
8/8, matching the frozen work-storage observations. The two accepted layout
tails are copied byte-for-byte. The frozen work-storage Result tail used
deliberately false zero array lengths to report layout through E0308; this
packet preserves its type expressions in an inert MIR signature instead and
retains the original tail. These are compiler inline layouts, not dynamic
backing prices or native allocation receipts.

`commands/` retains actual plans, stdout, stderr, tool identity, source/query
trees, terminal status, duration, owned PID/group and cleanup facts. Both rustc
children were reaped, both exact owned groups were absent, and owned scratch
was removed. No global process inventory or unrelated process manipulation ran.
The compiler reservation was released to root immediately after the two
terminal receipts; all later work was offline host inspection.

To verify a sealed packet without writing, compiling or running product code:

```sh
python3 -B verification/swift-guarded-snapshot-scoped-binding-source/check.py --read-only
```

The check verifies every sealed member, reproduces source/query manifests and
the complete MIR/layout/negative comparison from retained evidence. The packet
is sealed once and its files/directories are read-only. Independent review is
still required. A real bounded immutable input provider, native path encoding
correspondence, immutable identity review, whole work/storage source rebind and
pricing, P0 provisioning, accountable authority selection and executable closure
remain pending. Computer use, capture, simulator/emulator and physical phones
remain paused. Compiler-only host evidence does not qualify OTA, FieldLog,
published packages, operational deployment, final native acceptance, or GA.
