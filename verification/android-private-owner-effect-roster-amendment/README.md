# R1 roster amendment packet

This packet classifies exactly five frozen V1 IDs as compile/baseline-only and
explicitly retains all 184 other V2 semantic barrier records unchanged. It does
not implement or test product behavior. All C1/C2/focus/authority requirements and
the 14-actual-subject/73-substitute concrete closure remain unchanged.

`required-host-roster.json` contains the full active 184-entry V2 array and five
separately classified V1 entries with no V2 requirements. `v2-semantic-barrier-ids.txt`
lists all active IDs. `classification-proof.json` compares complete remaining
records, source anchors and all other predecessor fields. `receipt.json` binds
five prior seals, exact source inputs and tools. Historical 189-entry inventory
is retained under `inputs/`; no predecessor is modified.

Captured commands execute only bounded custody/classification checks, with retained
stdout/stderr. No product tests, native execution, source/profile/metadata/CI
changes, delivery or other external actions occurred. After sealing, verify only
this packet without rewriting results:

```sh
python3 -B verification/android-private-owner-effect-roster-amendment/seal.py check
```

Do not rerun capture or mutating verify after the seal. The packet is outside all
predecessor directories and adds no dependency beyond Python standard library.
