# Strict typed-join correction

This sibling supersedes the **utility implementation** from the immutable base
packet `fed4e7f1…39c5d`. Its source-specific 103-subject policy stays byte-identical
(`ada20df1…184e5`): all original cases/categories, 189 historical IDs, exact nine
editor replacements and the out-of-scope drain link remain.

Root's four exact counterexamples are retained in `root-findings.json`. The old
validator accepted Python `True` as BCI `1`, a floating opcode as the corresponding
integer, and contradictory actual subject/public outcomes on wrong-thread and
entry-refusal paths. No qualification flag became true, but the reported typed
consistency was incorrect. The base packet remains unselected and unchanged.

The corrected `typed_join.py` uses recursive exact-type structural equality for
policy objects and outcomes, and strict integral BCI/opcode types for every
caller/native tuple. Guard, constant, pure `getHandler`, wrong-thread and entry
refusal branches now reconcile subject/public values when both are present.
Native invocation tuples are validated even when the associated native outcome
is absent; a native outcome cannot omit its exact tuple. Main-thread constant
and wrong-thread refusal paths reject a native invocation even without a native
outcome. Numeric zero cannot masquerade as a false guard observation.

The public API and normalized schema remain as documented in the base packet:
`load_policy`, `normalize_rows(document)` and `validate_rows(policy, document)`.
The original 42 tests are retained, with 15 additional tests including all four
root rows, mutable policy numeric/container substitutions, native tuple types,
missing tuple checks, contradictory refusal values and nested snapshot types.

Run `PYTHONDONTWRITEBYTECODE=1 python3 test_typed_join.py` and
`PYTHONDONTWRITEBYTECODE=1 python3 test_corrections.py` from this folder. All tests
are host data-validator controls; synthetic rows grant no product behavior credit.
All row qualification flags stay false. Full policy matrix, actual missing body
outcomes, full execution source closure, native, OTA and GA gates remain pending.
No frozen packet, canonical/index, Git state, native runtime or paused capture
process is changed or started.
