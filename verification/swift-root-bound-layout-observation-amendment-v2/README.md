# Saved-raw observation amendment v2: bind evaluated memory

This separate source/offline correction addresses A01 and the explicit span-count
amendment from the frozen independent review, seal SHA256
`c0daaec0379bc1b51aa89669ccf617fa0eb78bba222b88e15365fa33c1331186`.
The entire first amendment remains immutable: all 22 members and seal SHA256
`298d2f3e9ac0f5ef0abacdeb24996d3a8d1031de02c91cb2cba82a62236a8723`.
Its plan was never released for actual parsing. All original/v2/v3 preparation,
source, saved raw, original rejection and review packets also remain unchanged.

The first adapter read the input into memory, then hashed the pathname separately.
A temporary changed read followed by restoration could therefore pass the path
checks while supplying different bytes to the parser. `input_bytes.py` now reads
at most the pinned length plus one, then requires the actual returned memory to
have exactly 292,318 bytes and SHA256
`05c526210b4c07779c09c33f1944ffaa06d8012c57a57e3ad05f68ee34106635`.
Empty stdout memory is pinned separately with a one-byte read ceiling. These
checks finish before the actual-call counter increments and before parser entry.
The independent pathname precheck and complete posthash/custody checks remain.

The parser now explicitly requires all 346 recursively source-verified spans,
matching the independently frozen retrospective oracle. The synthetic fixture
contains 346 valid geometries: each named error includes three additional
nonprimary source spans. Every span remains bound to immutable source coordinates,
highlights and excerpts. Valid missing/extra secondary spans refuse through the
346 guard; modified secondary source, bytes, highlight or excerpt also refuse.
The fixture uses arbitrary numerical layout values and reads no actual error
record.

All 116 earlier adverse controls remain. Fresh fake-reader tests hold the
separately observed path hash correct while returning wrong, short or overlong
memory; each refuses with zero parser calls and exactly one bounded read. An
expired deadline refuses before opening. Two positive memory controls cover
arbitrary exact synthetic bytes and empty stdout. Six fresh secondary-span
controls cover the exact count and source geometry. Final verification retains
126 adverse controls and two positive memory controls, plus a positive synthetic
whole stream with 346 geometries.

The literal policy is copied byte-for-byte from the first amendment. Exactly the
three complete warning objects at records 0/1/14, two independently anchored
19-byte transmute symbols, complete full-query and physical closure identity,
three exact summary/note objects, all 58 error bindings, strict JSON and numeric
guards remain unchanged. Warnings remain visible and counted as preexisting
baseline warnings. No original warning-free or original-pass claim is made.
`correction-delta.patch` is the complete seven-file code delta against the first
amendment, including the new bounded-memory helper.

`check.py` verifies the immutable first amendment and blocking review in addition
to the existing full saved-command/source/query/toolchain/Python/SDK/cleanup join.
No producer checker, compiler, child, version command, process query, native
runtime, UI/capture, phone or product code is run. Preparation runs only Python
source, custody and synthetic controls. No actual raw records are decoded in v2
preparation and no amended actual-stream parser call is made.

Only independent review and a separate exact root release may permit the one
offline actual saved-stream evaluation, under unchanged 20/45/51/55-second bounds
and zero compiler/child work or retry. Any output remains retrospective layout
candidates pending independent/root review, with `layouts_accepted:false`.
Prices, backing, peaks, funding, full ownership, native/device behavior, canonical
integration, FieldLog, OTA and GA remain pending.
