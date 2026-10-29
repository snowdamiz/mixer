# Bounded sibling delivery correction

Root selected two substantive changes after the original final source review:

- Remove only `verification/android-view-api-focused-actual-review/jdk-packaging-provenance/sources/runner-readme.txt` from `AUTHORED` and the exact `authored-check` argv. The immutable raw provenance snapshot has an extra blank line at EOF. Its source bytes and membership in all 74 staged and object-verified paths stay unchanged. The whitespace-check list contains the other 73 selected paths.
- The delivery receipt now records `manualWorkflowDispatchesAuthorized: 0` and `pendingSelectedDiagnosticDispatchCeiling: 1`. A future separately authorized diagnostic phase owns that ceiling.

The four sibling `_corrected.py` sources and three corrected phase manifests only add the necessary local filename, phase, output, pathspec and reservation-name substitutions around those two changes. Source inverse checks restore the original bytes exactly; manifest inverse checks restore the original data exactly. Command counts remain 22 delivery, 8 CI binding and 7 dispatch. The helper and accepted nine-command preflight pins are unchanged.

The original four sources, three manifests and original packet/seal remain intact. No authority was written and no commands, Python import/compile/runtime, preflight or dispatch ran during this preparation.
