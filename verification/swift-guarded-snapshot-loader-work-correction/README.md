# Receiver-specific loader callback correction

This packet corrects the **actual pricing tool** for the frozen loader-work
proposal. It does not edit the46-member producer packet or execute its scripts.
`custody.py` rehashes every original member, the complete/selected compressed
MIR and the root finding before pricing. Full source/MIR remain referenced
immutably, with no duplicate source tree or compiler invocation.

The frozen input seal is
`0550b44baf9f576d8379e1dd93f89ea9bd5b48ff7367762ae008181d29d2c30c`.
Root finding SHA256 is
`aac057a0cf4727a054a8998a02a0fd6da947ed15ac978e8080fe017c83b784ed`.
Both remain exact source145/host11, tree
`450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a`,
with the same219 complete MIR definitions. Original failures and rejected token
counting remain intact and bound by the original seal.

## Defect and direct correction

The original `resolve(target)` searched for an authored equality type anywhere
inside the target string. Consequently both `wresolve` comparisons
`<&[Type] as PartialEq>::ne` matched the scalar `Type::eq` body at multiplicity1.
The intended128-callback fallback was then unreachable. Root chose a direct
correction; no native-name slack is reassigned or reduced.

`receiver.py` parses the exact supported PartialEq receiver and RHS shapes
before scalar dispatch. The adapted `price_mir.py` uses this classification in
both its actual product resolver and callback emitter:

| Receiver | Authored Type callbacks |
| --- | ---: |
| Direct Type | 1 |
| Option<Type> | at most1 |
| &[Type], selected signature ceiling | at most128 |
| &[Type] compared with fixed [Type;1] | at most1 |
| Explicit frozen primitive/std element shapes | 0 authored callbacks; existing primitive/native work retained |

Other authored scalar receivers resolve by their exact type. Unknown,
unsupported or ambiguous receiver/RHS shapes refuse. The classification is for
these frozen MIR targets, not general verification authority for new code or
new equality implementations.

Wrapped Option/slice equality remains a standard primitive with an explicit
Type equality callback edge. Scalar equality remains the authored scalar call.
The original403 standard target roster becomes407 because four existing
wrapper target strings are now properly classified as standard wrappers. This
reclassification changes only call entry labels, standard-call diagnostics and
callback diagnostics; numeric callback multiplicity changes at exactly the two
identified slice sites. The wresolve callback maximum diagnostic becomes128.
All local/type/operand/native/repeat/source/MIR terms remain identical.

## Exact numerical increase

The authored Type equality body remains104 logical actions. The two corrected
edges add `2*(128-1)*104 = 26,416` to the fully expanded validator coefficient.
No other expanded numeric term changes:

```
W_wrapper                    97,394,558,768,720  unchanged
old C_validator                   1,747,993,923
new C_validator                   1,748,020,339
new W_validator_host        894,986,415,316,020,339
old W_loader                895,070,284,882,762,643
new W_loader                895,083,809,874,789,059
delta                        13,524,992,026,416
```

For every admitted original credit limit B, the exact delta is
`(B+1)*26,416`, with checked u64 arithmetic. These are conservative logical
source/callsite/requested-byte terms, not measured or feasible performance, CPU
work, wall time, RSS or a selected host budget. Product limits do not change.
`mir_quote.py` and `quote.py` are byte-identical copies of the original pure
arithmetic/evaluator tools; the regenerated ledger supplies the correction.
`delta.json` records both exact quotes and changed fields.

## Projection qualification and remaining review

The original prose that charging the whole base local covers projections is
**not a general proof through references**. A reference local represents a
reference place, not an enumeration of its referent's fields. Aggregate reads
through a reference need the actual source/MIR operation, destination or typed
temporary surfaces to establish coverage. The ongoing independent review is
checking those exact actual sites through typed temporaries. This correction
does not infer a generic verifier rule, add reference-pointee funding, change
those terms or preempt the independent callsite conclusion.

`python3 verification/swift-guarded-snapshot-loader-work-correction/run_checks.py`
runs only the new read-only custody checker, adapted pricing tool and focused
pure regression checker. The2,521 controls include rejection of the original
two×1 model, acceptance of two×128, direct Type/Option/fixed-array controls,
unsupported shapes, exact all-node/call/native invariance, counterfactual
restoration of the old scalar, monotonic B grids, overflow, unknown callees and
cycles. They also verify all46 frozen producer members. These are finite
arithmetic/custody/regression checks, not independent source acceptance or
product behavior tests. No original producer script is imported or replayed.
Exact commands, tool hashes, Python version, outputs and timeouts are recorded.

This remains a source145 proposal. Root's separately accepted source146
composition still requires an explicit quote/source/descriptor/fixture rebind.
The host-account work component remains pending until root accepts the full
review and final binding. No operational grant, physical/native/UI/capture
runtime, loader/validator/VM/cache/scope/constructor/writer execution, global
process inventory, publication, customer message or GA qualification occurs.
No scratch runtime or native instances were created. No compiler or Git command
ran; all files written are inside this new correction folder. The original
producer packet, canonical source and active independent folder remain intact.
