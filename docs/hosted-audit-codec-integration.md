# Hosted upload audit codec candidate

This isolated candidate moves the reviewed storage specimen's fixed audit codec
into `MixerHosted.Audit.UploadEvent`, without changing live hosted source. Its
three pure functions decode a closed display map, validate a retained row and
validate the immediate predecessor edge. They return a fixed error on malformed
input and confer no identity, signature, membership or release authority.

The candidate preserves the accepted PostgreSQL string escaping, UTF-8 bytes,
map ordering, typed CBOR field order and domain-separated hashes. The existing
artifact CBOR encoder and every existing hosted file remain unchanged. Byte
strings and nulls belong to this audit schema and do not widen the artifact
encoder's supported data model. No new dependency is added.

Unlike the synthetic specimen's general helper entrypoints, the new public
surface only accepts the closed audit representation. It checks the 16 display
keys, fixed array lengths, at most 64 ordered unique memberships and every field
bound before formatting. Proper-list checks stop at the configured length;
oversized text is rejected by byte size before UTF-8 scanning. Stored digest
fields are bounded before hexadecimal conversion. CBOR is limited to 16 KiB and
display bytes to 32 KiB. These bounds constrain processing and output; caller
inputs are already allocated and this is not a total BEAM memory limit.

`decode/1` reconstructs CBOR and checks the supplied event hash, then returns the
exact CBOR, hash and display bytes. `validate_row/1` additionally checks the
closed ten-field row, tenant/event ID/projections, exact retained bytes and the
first event's initial state. `validate_edge/2` validates both bounded rows,
same tenant, adjacent IDs and matching previous hash/state. A nil predecessor is
permitted only for event one. This is consistency under the separately selected
append-only storage contract, not protection against an administrator coherently
rewriting history.

The final isolated run passes **11 focused tests** and the complete hosted suite
with **104 passed and two explicit Linux-only network-namespace skips**. Formatting,
warnings-as-errors application compilation, packaged release construction,
missing-configuration rejection and four test-export exclusions pass. The owned
PostgreSQL fixture and all scratch are removed. The full suite's SQL exercises
existing hosted foundation behavior; the audit codec consumes captured SQL rows,
not a newly implemented audit writer or migration.

The focused tests reconstruct all **185 actual PostgreSQL rows in six chains**
from the frozen independent formatter review, including control characters,
Unicode and maximum reason/profile boundaries. An independently authored Python
oracle builds **80 coherent-hash vectors: 10 valid boundaries and 70 rejected
schema cases**. Their hashes match their mutated CBOR, so negative cases do not
pass solely because of a stale hash. Additional tests cover oversized/improper
containers, malformed UTF-8/NUL, numeric spelling and limits, UUID/digest/role/IP
domains, exact display-byte corruption and a separately valid foreign-tenant row.
The fixture generator imports only the previously reviewed independent oracle;
it never imports the candidate encoder.

All five attempts remain retained. Attempt 1 rejected the collector's incorrect
dependency count (21 pinned packages, not 22). Attempt 2 lacked Hex installation
metadata after archive extraction; offline locked dependency setup now supplies
that metadata, with unchanged lock and rechecked source hashes. Attempt 3 exposed
a test fixture error: a supposedly foreign predecessor was byte-identical to the
valid predecessor. Attempt 4 exposed another test fixture error: uppercasing an
all-zero digest did not create a malformed spelling. Both were corrected without
weakening the assertions, and the original failing source/output is retained.
Before attempt 5, source review also added explicit retained-digest size guards.

The [receipt](../verification/hosted-audit-codec-integration/receipt.json) binds
the exact overlay, original source, dependency archives, commands and logs.
The [checker](../verification/hosted-audit-codec-integration/check.py) verifies it
without starting services. A new replay uses an unused numbered run:

```sh
python3 -B verification/hosted-audit-codec-integration/check.py
python3 -B verification/hosted-audit-codec-integration/run.py 6
```

Independent review and root integration acceptance remain required. Complete
production AS05, selected catalog/migration, authoritative writer/repository,
authenticated HTTP, Neon/R2/Cloudflare, Oban, native and physical-device checks,
published FieldLog packages and all GA gates remain pending.
