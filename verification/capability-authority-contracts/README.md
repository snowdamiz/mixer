# Capability authority contract audit

This original checker verifies the frozen four contract definitions and their
design reference. It performs 241 static assertions, including closed field sets,
cross-file digest bindings, six capability import signatures, preserved legacy
imports and grant bytes, resource ceilings, separate close-work accounting and
the exact zero-page narrowing rule. These are static assertions, not 241 runtime
test cases or permission to execute a release.

The source pin is `check.py` SHA-256
`38a5575bf882a21f3b2f763a25287c5319d0f91613b6d9b26efcdf9074ce52a8`.
The script checks its frozen inputs before and after the audit. It also compares
all eight previous contract files byte for byte with committed revision
`1ab4d4ee76a5d4ba206bd370cbeeeb73a7c6c636` using `git show`, and checks eight
additional frozen headers, profiles, schema and builder inputs. Each receipt
contains all source digests, tool versions, commands, output hashes and scope.

Both retained runs passed all 241 assertions:

| Invocation | Receipt | Receipt SHA-256 |
| --- | --- | --- |
| Python | `2026-10-23-frozen/receipt.json` | `209446c17cdc0f33dbe8a5ffc78b8e46d48e9dd91330c49685438d207cb7f0cb` |
| Python `-O` | `2026-10-23-frozen-optimized/receipt.json` | `698b9ad86ce9238503e9123ef76ef5a55aeb1c1321b8485633cf883bd2f5d406` |

Replay from the repository root with Python 3.11+ and fresh output paths:

```sh
python3 verification/capability-authority-contracts/check.py --output /absolute/fresh/audit
python3 -O verification/capability-authority-contracts/check.py --output /absolute/fresh/optimized-audit
```

Guards use explicit exceptions, so optimized Python does not remove them. Each
successful output includes `checks.log` and `receipt.json`; failures retain a
`failure.json`. The five frozen definition/design hashes are recorded in the
script and receipts. This evidence adds no implementation, parser acceptance,
build attestation, native effect, actual health, full Swift/UI/FieldLog, device,
publication or GA qualification. The separate independent review is under
`verification/capability-authority-contract-review/` and is not counted here.
