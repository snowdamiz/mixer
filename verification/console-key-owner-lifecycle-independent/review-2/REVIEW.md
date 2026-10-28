# Independent review of lifecycle correction candidate 2

R01 is closed for the released source. No blocking findings remain. Recommend
root release of one exact bounded host execution of plan
1ae8bd1e9e38c2a18abae465b054fdcf562b842972475bc9bc1d3e80c07a52b3,
under producer freeze
d59a6d3987a3dd892b24bc2fbefba079926dcbb8ade28ad9c429ddd4a54f19ef.
This recommendation is source/runner acceptance for execution, not a runtime
release or product behavior pass.

The thirteen artifact schemas are byte-identical to the independent review-1
schemas. validate_terminal_artifacts requires the exact artifact-path set, exact
field sets, true/false identity, integer types excluding booleans/floats, and
exact strings or accepted successful cleanup-result strings. Incomplete/empty
maps, unknown suffix-result keys, absent runtime fields, boolean zero counts,
float counts, and wrong string values fail closed. Schema loading remains
strict about duplicate/nonfinite JSON and uses the pinned prepared file. A
validator exception enters the runner's existing failure finalization path and
does not hide retained artifacts/output.

The controls source was read, and its source-bound report was reviewed without
replay: two good aggregate fixtures cover successful :ok and :already_stopped
cleanup results; 711 distinct malformed fixtures cover aggregate types/path
membership, each artifact's malformed map and missing/unknown fields, each
field's bad type/value, and the exact review counterexamples. Four separate
JSON controls reject duplicate keys, NaN, Infinity, and -Infinity. These remain
producer pure-Python observations, not fresh independent replay or product
runtime evidence.

The read-only formatter amendment operates on exactly the three authored staged
canonical source/test files in the corrected existing VM using
Code.format_string! with default options and final-newline equality. The pinned
hosted/.formatter.exs contains inputs only and is not evaluated. The actual
order is after ExUnit, postconditions, and Mix.State stop, before successful
phase exit. Root explicitly accepted this exact order during review. A format
failure can leave observed test results in retained artifacts, but its raised
error makes the corrected process fail; the outer runner cannot report that
phase clean. No extra phase, VM, product test, or write is added.

Independent read-only custody audit passed all 234 new freeze members, 233
prepared members, 216 canonical pins and 969 tool pins. The entire old 224-member
packet remains unchanged. Of its copied nonplan members, 221 are unchanged and
only runner.py/bootstrap.exs differ, exactly as selected-correction.diff records.
All eighteen product sources, the dedicated seven-case suite, both original
beforeimages, original phase/bootstrap, compile-common.exs, five dependency apps,
deadline partitions, signal handling, and owned-resource cleanup remain as
reviewed in review-1. The additional canonical inputs are the formatter file and
independent review evidence. Product/test bytes still equal canonical files.

No producer Python was imported or replayed in this review. No compiler,
formatter, Elixir/BEAM, version process, DB, network fixture, native/UI/capture,
or process inventory ran. The next root-released execution must retain actual
versions, compilation diagnostics, original defect witness, corrected seven-test
counts, formatter result, full output and exact cleanup. KOL08/KOL09 active
flight/TLS/fault behavior, actual app/provider/HTTP/browser/session/operations,
physical devices, and all GA gates remain pending.
