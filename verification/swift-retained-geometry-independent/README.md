# Independent retained geometry local-facts review

The two frozen candidate packets pass independent source/native and local-facts
review within the scope below. Root acceptance is pending. This is not a complete
region certificate, an executable verifier input, a numeric union, a whole-call
capacity result, or runtime admission.

Inputs are exactly Caller/Closure seal
`31c93475b603342a50d943d8050ff43cdcfe932703bd56fb10f8785b7c09f964` and
Dispatch/Body seal
`0824b778f47268ddf3f94d6a51ee5f6d64553efb0440d89179012c0824ec3517`.
Both use the identity-accepted alternate diagnostic capture, whose only changed
compiler option is `-C link-dead-code=yes`. The source manifest remains 146 members,
tree `91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f`.
The original capture remains unqualified, and the selected quote source still
returns `WholeQuotePending` at host_account_v1.rs:76.
The exact saved argv also changes the two owned output paths, and the environment
changes only `TMPDIR` to the alternate-owned command directory. Both exact argv
and environments are retained in `configuration-review.json`.

## Review and integrity evidence

The reviewer read the complete Caller, Closure, Dispatch, and Body IR and assembly,
their source spans, and the whole Body exception table. Full function displays
completed without truncation. Some exploratory multi-file metadata displays were
truncated; no finding depends on those partial displays. The independent audit
hashes complete artifacts and compares all supplied raw anchors.

The recorded audit command is:

```
python3 -B verification/swift-retained-geometry-independent/audit_review.py
```

It uses only Python standard-library file/text/hash operations, with a 50-second
alarm and 55-second command ceiling. It does not import or execute producer code,
selected source, a verifier, compiler, native program, model, or tests. It runs no
version command, process probe, UI automation, capture, simulator, emulator, or
device. No native instance was started, and no cleanup is owed.

The audit rechecks every one of the 32 sealed geometry members, their two seals,
146 current source members, all eight whole native spans, four source spans, and
the complete Body exception table. It verifies 546 supplied raw-anchor occurrences
(366 distinct), the 199 saved debug lines directly in streamed raw IR, and each
whole native function's global line coordinates. Complete native/IR call counts
are Caller 8/9, Closure 1/2, Dispatch 5/5, and Body 37/37; IR counts include
intrinsics, including in-function copies that do not lower to external calls.
The distinct raw pair is 111,430,754 bytes, below 128 MiB, and is never copied.
Derived review output stays below 8 MiB. Relevant inputs are rehashed afterward.

## Accepted local facts

1. Caller reserves 14,000 bytes: saved state 32 + three actual 4,096 decrements +
   1,680. Closure reserves 48. Dispatch reserves 41,024: saved state 32 + ten
   finite probe-loop decrements of 4,096 + 32. Body reserves 63,920: saved state
   32 + fifteen such decrements + 2,448. These follow native SP instructions;
   LLVM alloca sums are not used as frame or transitive bounds. Each sole normal
   return restores entry SP. Caller has three normal CFG routes to its common
   epilogue. No extra outgoing SP allocation appears in these whole functions.

2. The Caller slots, Closure attempt copy, all five Dispatch allocas and seven
   native spills, and all 46 Body allocas and 28 native spills map consistently to
   the complete native instructions. Body's four unassigned padding intervals and
   internal exception-record padding remain padding. Representation storage is
   distinct from the validity/alignment requirements of accesses.

3. With entry bases `E_C`, `E_D`, `E_L`, `E_B`, the emitted direct-call chain gives
   `E_D=E_C-14000`, `E_L=E_D-41024`, and `E_B=E_L-48`. These are reviewed signed
   instruction-coordinate relations for that exact generated success chain.
   They provide no physical base congruence or runtime reachability.

4. Caller constructs the 48-byte capture at `E_C-200`: fixture at 0, attempt bytes
   at 8..40, expected pointer at 40. Dispatch copies all 48 bytes to `E_D-27344`
   and passes that record to Closure. Closure copies the 32-byte attempt into its
   own `E_L-48` slot, loads fixture/expected, and forwards its incoming x8/%_0
   unchanged to Body. Closure allocates no result carrier.

5. Dispatch supplies R at `E_D-40968`, capacity 13,624. Thus R is 104 bytes above
   Body entry SP and belongs to the still-active Dispatch frame. Body saves the
   incoming pointer at finalSP+168. Both normal local constructions copy a
   13,616-byte payload representation and store the 8-byte root at offset 13,616.
   Its 13,616-byte local stages are distinct; there is no local 13,624-byte alloca.
   This accepts emitted storage/copy coverage, without proving external callee
   write-completeness or that padding/inactive enum bytes are initialized.

6. Dispatch copies R through two distinct 13,624-byte staging slots, then to C,
   and writes the two reservation words at C+13,624 and C+13,632. Caller supplies
   C at `E_C-13840`, capacity 13,640, and copies it to its incoming outer sret O
   after Dispatch returns. The two refusal calls receive O directly. O's concrete
   allocation, offset, extent proof, alignment, physical relation, lifetime, and
   later destruction remain unresolved.

7. Native reservations persist through their activations; source moves and debug
   lifetimes do not release them. C survives Dispatch return until Caller's outer
   copy. Copying pointer/descriptor carriers preserves backing identities and
   proves no extra backing allocation, capacity, or healthy destruction.

8. Caller, Closure, and Dispatch contain no local language cleanup/resume path.
   Body's normal return restores SP, but its cleanup calls `__Unwind_Resume` at
   `E_B-63920`; termination calls `panic_in_cleanup` there too. No explicit +63,920
   restore is invented for either outgoing edge. The full CFI/LSDA, four cleanup
   landingpads, conditional drop order, and termination landingpad remain
   separate from unproved external unwinder/destructor/OS behavior.

## Preserved limits and next step

All packet review flags remain false in their frozen original bytes. This review
records its scoped decision separately; it does not rewrite those packets.
Every candidate arena retains `physical_alignment=null`. Required LLVM alignment,
SP offsets, q-register accesses, and CFI do not establish actual entry congruence.
No numeric interval union, phase peak, sum of active frames as capacity, price,
quote, grant/refund, root funding/custody, complete backing graph, or GA result is
accepted. All thirteen source-conditional backing obligations and ten retained
partitions stay pending. External callees, probes/guard faults, allocator/OS
backings, later child destruction, and all unwind continuations remain unbounded.

The initial Dispatch/Body preparation failure is retained verbatim in its sealed
`preparation-attempt-1.json` and copied into this audit receipt: it expected the
preliminary peer seal `6468bc27...`, observed final `31c93475...`, exited 1 before
posthash/seal, and required the separately frozen final peer reference. The later
successful preparation does not turn that failed attempt into a pass.
`audit-attempt-history.json` also retains this review's exploratory missing-file
read and its later overstrict whole-environment assertion failure. The latter
stopped on the owned `TMPDIR` difference; the final audit checks every other field
for equality and verifies both explicit `TMPDIR` paths without relabeling them.

The existing v2 verifier still has a closed original binding: plan `bed9476b...`,
argv `4022ae10...`. Its equality/schema checks necessarily reject the alternate
plan `15413684...` and argv `799f61fd...`; no invocation was needed or performed.
The separately owned adaptation must retain explicit alternate provenance,
unknown congruences/O relations, all copy stages, and Body's outgoing unresolved
unwind/termination edges. This review neither edits nor approves that adaptation.

The concrete next step is root acceptance of this exact sealed local-facts review,
followed by independent source review of the separately frozen alternate-binding
adaptation before any new bounded host invocation is selected. A numeric union
still requires actual reviewed congruence/arena/coverage/exit evidence and trusted
root approval. Device and paused native runtime checks remain pending. Product
source, global metadata, other lanes, frozen packets, commits, and pushes were not
changed by this review.
