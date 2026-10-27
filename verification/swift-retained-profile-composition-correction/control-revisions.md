# Exact raw witnesses and required control adaptation

The three R01/R02 method bodies are copied byte-for-byte from the29-member
independent review into both old/test_independent.py and
corrected/test_independent.py. run_unchanged_witness.py imports one exact method
per owned subprocess without invoking the witness's original main or writing into
either frozen packet. Raw old and corrected streams/results remain under
raw-witnesses/. No assertion is changed in these raw executions.

R01 needs no behavioral revision. It still requires natural same-order number
reuse, closed old wrapper refusal, fresh owner usability and no hostile path race.
The correction additionally tests the actual retained composition entry, read,
seek, borrowed I/O, child lease/adoption and idempotent old close after reuse.

R02 has two finalizers which assume the old broken cleanup left every ancestor
open and that OPEN_FDS is mutable close authority. They directly close numbers
again and remove accounting entries. After a correct implementation closes all
independent ancestors, that finalizer can close an already closed number or,
outside the narrow old witness's known schedule, a number reused by another owner.
The corrected accounting view therefore refuses removal. Those raw finalizer
errors stay visible; they are not corrected-source behavioral passes.

The pre-close witness also calls fstat on held.fd after close began. The corrected
held.fd is a generation-bound borrow, so it must refuse all OS operations after
close begins. The test still knows the **captured pre-close raw number** and
exactly whether its own injected stub executed os.close. It may use that separate
controlled test oracle before any new fd opens; it cannot use an invalidated
wrapper borrow to authorize the observation.

The separately implemented adaptation in fault_case.py is exactly:

1. Capture the owned number/token set before closing and retain the exact injected
   exception object and pre/post stub execution trace.
2. Keep the original assertions: all independent remaining ancestors are actually
   closed; a pre-syscall unclosed leaf remains accounted. In the65-position matrix
   assert every independent remaining descriptor closed, not merely the first
   leaf; assert all65 close calls attempted once.
3. For the pre-syscall oracle only, fstat the separately captured raw test number
   before any new open, because the closed wrapper borrow is intentionally dead.
   Require its token remain uncertain/accounted and healthy_zero remain false.
   A post-syscall oracle must likewise leave uncertainty, despite known actual
   closure. This observation never becomes a generic kernel-fault classifier.
4. Remove the numeric-retry finalizer. Do not close an uncertain saved number,
   erase its registry record, change the wrapper back to open, or clear a lease.
   The bounded host subprocess exits and is terminally reaped after observations.
   Directory/process cleanup is reported separately, not as successful ambiguity
   resolution. Modeled uncertainty deliberately remains nonzero at process exit.

The test harness's final assertion thus reports expected unresolved modeled state
for a fault case rather than pretending reviewer cleanup proved healthy zero.
This strengthens the lifecycle requirement while preserving the two original
behavioral assertions. It does not weaken them into expected failure, skip them,
change the fault schedule, or call a leaked descriptor acceptable.

The nonterminal child model's old reviewer cleanup assigned live=False and closed
the wrappers by fiat, despite having no real stuck child. The corrected live
property has no public setter; only the actual lease's terminal path releases it.
Its contained model verifies the original wait/kill counts and both leased owners,
plus preservation of the original unreaped refusal and both cleanup refusals,
then exits the test process. It does not manufacture a terminal child receipt.

All26 original producer methods are unchanged and pass; their healthy cleanup
expectations still require zero. Fault-case cleanup states are separate from
those healthy assertions. There is no real OS close ambiguity retirement policy
or product authority selected by these synthetic controls.
