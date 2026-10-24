# Retained audit display formatter correction

The isolated correction resolves CR01 in the local synthetic atomic-storage
specimen. The [full run](../verification/hosted-atomic-display-correction/run-3/tests.json)
passes **88/88 cases**, with no skipped or excluded cases: all original 83
assertions and five added display cases. Independent review and root acceptance
remain pending. No live hosted implementation or product/GA gate is accepted.

The [selected contract](hosted-atomic-display-correction-contract.md), final
[independent review](hosted-atomic-storage-correction-review.md), and all frozen
producer/reviewer bindings are retained in the
[packet](../verification/hosted-atomic-display-correction/receipt.json).
The fresh unchanged baseline reproduces 81/83 with I02/I03 failing. The
[formatter-only patch](../verification/hosted-atomic-display-correction/formatter-only.patch)
replaces string encoding in the independent expected-byte formatter. It walks
validated source bytes, escapes quotes and backslashes, emits the standard short
control escapes, spells other representable C0 controls with lowercase four-digit
hex, and copies UTF-8 literally. Object keys use that same formatter. Literal
backslash-u text retains its original text and case. NUL and malformed UTF-8 are
explicitly invalid PostgreSQL storage inputs. The closed schema's key ordering,
spaces, arrays, integer schema value, null and exact retained-byte equality are
preserved. SQL, catalog definitions, CBOR encoding and stored bytes are unchanged.

The five new assertions establish the following scoped results:

- Actual PostgreSQL byte parity for each U+0001–U+001F control and U+007F,
  quote/backslash/solidus, ten literal-escape cases, twelve UTF-8 cases, and one
  combined string; 56 cases also cover both reason and profile and a separate
  escaped-key/nested-value example.
- 56 actual distinct artifact uploads retain every row column, pass both row
  validators, and replay the original status/body/event with unchanged rows.
  An adapted Python standard-library oracle checks these 56 rows and the eight
  original reviewer rows independently of the candidate encoder: CBOR, standard
  hashes, projections, exact display bytes and adjacent edges all agree.
- Profile/reason limits remain 128/512 source bytes, including control escape
  expansion, multibyte UTF-8 and literal escape text. Two 512-byte reasons also
  upload and replay; 129/513-byte violations reject. The original CBOR/display
  limits and corruption cases remain in the preserved suite.
- Actual PostgreSQL rejects U+0000, five malformed/NUL JSON escape inputs and
  four malformed UTF-8 inputs. A valid surrogate pair remains a valid UTF-8
  control. None is represented as a successfully stored invalid row.
- An uppercase substitute for a retained lowercase control escape still rejects
  in both row validators despite decoding to the same JSON value. Restoring the
  exact original bytes restores the exact cached replay.

All original positive, rejection, timing, privilege, confirmed wait/pre-DML,
completed-COMMIT acknowledgement-loss, owned server restart and unchanged replay
assertions pass. The unchanged catalog digest proves equality to this frozen
synthetic specimen only. It does not qualify production startup inspection,
trigger enablement/internal FK state, persistence classes or authority-schema
catalog hardening.

The first expanded attempt passed 87/88. Its new D05 assertion expected a boolean
`false`; the unchanged SQL `row_valid` correctly raised `P0001` for corrupted
bytes. Only that new assertion was corrected to require an error. That failed
attempt, the baseline failures, exact per-attempt sources and outputs remain
frozen. The formatter did not change after the first expanded attempt.

Run `python3 -B verification/hosted-atomic-display-correction/check.py` for the
read-only frozen checker. Run
`python3 -B verification/hosted-atomic-display-correction/run.py` for a fresh full
88-case disposable PostgreSQL execution, `run.py --focused` for the five tagged
new assertions (83 prior cases explicitly excluded), or `run.py --baseline` to
reproduce the original 83-case failure with the frozen original codec. Each run
creates a new numbered attempt and preserves failures; re-freezing requires
review of the new results. The runner uses the accepted dependency archives,
verified installed source copies, frozen legacy sources and unique owned scratch
paths. It records exact argv/environment overrides, executable versions/hashes,
source/dependency/contract closure, output hashes and owned cleanup. No network
dependency fetch or live hosted build is used.

All owned PostgreSQL/proxy/scratch/socket resources are cleaned after every
attempt. No native run or simulator was started, and no other project's process
was touched. Physical phones remain disconnected and deferred. This packet is
limited to local synthetic PostgreSQL/Ecto mechanics: authoritative credential
and membership resolution, product migrations/repositories/HTTP, signed admission
composition, Neon, Cloudflare, R2, Oban lifecycle, FieldLog, external security,
operational and GA qualification remain separate outstanding work. Fresh
independent review and root acceptance are required before integration.
