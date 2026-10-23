# Independent six-option accounting and cache-v3 audit

Decision: **accept the frozen private foundation accounting correction and cache
contract v3 only**. Cache implementation, executor implementation/composed live-set
maps, target execution, physical devices, published consumer and GA are unaccepted.

`receipt.json` binds the source/log/tool/probe artifacts. Root's immutable input
receipt SHA is `c5220730687db18698753e62a2c02acec1575290e30a6e92fcec35c097127828`,
with source tree `5aac67fdd716e6b85285bea51e0245284f9a9dbf1971ceebffafcda9f5005b1d`.
All 417 VM files match committed `3a1bb5a` except the two expected overlays:
control `55e0e89c5da57347f02fd13dfb97296c19c3ace7d94fc11109dd224c9046b79f`,
tests `0618d894583264b194d69f90c7a29a01a6a62f96a6118c337a508c5b910236b7`.

The control bytes differ only by replacing two raw WasiUsage shapes with six
Option<WasiUsage> shapes and their explanatory comment. Stored types/layouts,
public/private routes, work order, ticket count and cleanup algorithms are
unchanged. On the recorded Apple arm64/Rust 1.99.0 host, optional=112 versus
raw=104; the upfront foundation is 16,504 instead of 16,040 (+464). Five nested
observed-control parameters plus one retained caller observation are counted
without last-use/compiler-elision assumptions or borrowing another component's
envelope. Other caller copies remain their own named-envelope obligation.

The independent audit reproduces all **859** root source/log/result bindings and
the 12 successful command records: 320 full plus nine reference checks per mode,
73 minimal-Swift checks per mode, named layout/admission, scoped lint and format.
It runs the root admission test against the pristine frozen source in Debug and
Release, then runs **30 control tests per mode** against that source plus one
independent three-case probe. Existing actual eleven-case instruction/fuel,
cancellation/deadline, sticky cause, capacity, cleanup and ownership tests are
included in those control runs.

The independent probe constructs one genuine accounted WASI owner, performs
ArgsSizesGet, retains its actual final observation, then **destroys that owner
and its header before** standalone control admission or proof-refund faults.
The three cases exercise deep cache-entry/category admission, source refund and
metadata refund with the source-result wrapper retained. Both refund invariants
use test-only damaged ledger scalars, never fabricated proof/ticket authority.
It verifies actual observations, no runtime allocation, immutable first failure,
continued draining and conservative residual charges after corruption. The valid
owner admission-failure cleanup reaches zero. These host tests instantiate no
guest target and run no initialize/corpus function.

Cache v3 is bound separately to its new producer receipt
`94476317a7bf4ea59266e7cad2f75d99bfae8196bd05abd21df4f64ed40628a3`:
18 bindings, four successful commands and its exact archive were independently
checked. Exact doc/checker/acceptance bytes were copied before replay. The checker
and three artifact tests pass, with **36** deliberately invalid plans rejected,
including raw/two/three/five optional shapes, last-use assumptions, borrowed
envelopes and rewritten history. Eighteen cache implementation tests remain
pending; artifact success is not their execution or acceptance.

The historical-v2 manifest hash remains
`beb7f4c95a321108868aaeb4e92ccd1f8e85b0d6259164409c20c0b2f84935b1`.
All six archived v2 files and the original root freeze bind exactly; v1 history
also verifies. The old v2 proposal receipt is historical only. The new v3 receipt
is not retroactive evidence. Root source acceptance/freeze remains recorded by a
separate root decision rather than modifying the proposal's pending fields.

No source, contract, producer receipt or previous reviewer artifact was edited;
all new files are in this review directory. No collector was run. Frozen inputs
are retained in `review-inputs.tar`; build output is ignored under `.build/`.
Reproduce with `python3 verification/swift-observation-accounting-review/review.py`.
Reviewer: fresh bounded gpt-6.1-sol, xhigh.
