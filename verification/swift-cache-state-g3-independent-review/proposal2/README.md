# Independent proposal2 disposition

The exact620-byte unwrap macro is locally consistent within the same disclosed
source-operation model. The independent partition has64 named scalars in four
16-operation blocks plus four8-byte payload copies; short paths use33/35 scalars.
Explicit usize, one offset evaluation, hygienic c access, all initializer/result
edges and original short-circuit/read order reconcile. No headroom remains.

Any successful at..at+8 access yields exactly8 bytes, so first_chunk::<8> is
Some. Full seed/cursor/copy induction also bounds admitted reads. Replacing expect
with unwrap changes private panic text only on impossible None; it removes the
explicit message argument rather than assuming it optimized away.

This is bounded implementation-design evidence. The binding contract does not
formalize the favorable whole-Range/full-view/Option primitives. A separately
charged receiver or other new operation breaks64. Local merge120/helper144
arithmetic does not establish the complete29344 role union or compiler layout.
`grain-and-ownership-review.json` names every complete control owner and makes
the root model choice explicit. Merely expanding each Range/view row to two
field operations gives72; that sensitivity is not a new mandatory rule or a
complete alternate upper bound. No physical/register micro-operation claim is
made for a whole16-byte primitive, and no independent copy disappears.
Actual G3/source/lifetime/implementation acceptance is false. Root must select
any source edit and separately admit fresh compile/API/layout/behavior evidence.

Reproduce static checks only:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-g3-independent-review/proposal2/build_review.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-g3-independent-review/proposal2/verify_review.py
```

Builder writes only proposal2; rebuilding changes custody time/HEAD and requires
resealing. Verifier validates frozen bytes and arithmetic. No product/compiler/
harness/model/native/device execution or process inventory occurred. Active
correction2 writes were not read. Prior review/proposal packets remain immutable.
No release/dogfood/GA qualification is supplied.
