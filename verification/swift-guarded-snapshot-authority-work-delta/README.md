# Consuming owner capability: work delta proposal

The accepted authority correction adds **19 source-action credits**, once per
consuming construction, under the existing writer audit convention. This is a
separate proposal for the corrected source; it does not accept the original
writer ledger or replace `WorkAuditPending`.

The scope constructor's prior 16 actions become 21: four token aggregate fields
and one local binding are new. Its existing cache/control/WASI borrow expressions
move into the token literal and remain charged once. The prior forwarding chain's
five actions become 19: the new consuming helper costs ten (entry/return, four
field pattern bindings, four tuple output slots), and the inner caller binds four
tuple fields. Existing call boundaries and the selected branch output slot remain
charged once. Owned values move through parameters without deep-copy charges;
the convention makes bound local operands free. No token Result/Option, retry,
new encoder call, stop check or native operation is invented.

Combined scope/forwarding bookkeeping is therefore 40 rather than 21. The source
work occurs before phase planning and needs explicit pre-admitted funding in the
final integrated recipe. These credits are not added to encoder initialization,
writer per-block work or each write attempt. Original construction and cleanup
bodies keep their separate inherited attribution.

`check.py` binds all four exact corrected function bodies and original rows,
checks the arithmetic and rejects missing/doubled named action categories. Its
finite source checks do not authorize an OTA release. Independent review of this
proposal, complete storage/work selection and genuine writer tests remain pending.
