# Customer artifact transaction proposal evidence

This packet describes the next protected operation. It implements no product
storage, route, migration or audit codec and passes no product/GA gate.

`observed-inputs.json` pins the 21 named ordinary sources reviewed at the base
revision supplied by root. Frozen catalog-inspector/authority-driver and rejected
Worker lanes were neither read nor executed. No Git, provider, UI or native
action occurred in this lane.

Validate the document and the 35-case executable test plan:

```sh
python3 -B verification/hosted-customer-artifact-transaction-contract/verify.py
```

Use `--check-observed-source` only to compare the live named inputs with the
review snapshot; concurrent root/facade changes can correctly report drift.

After implementation, execute the declared ExUnit suites from this same runner:

```sh
python3 -B verification/hosted-customer-artifact-transaction-contract/verify.py --run-implementation
```

The implementation mode currently exits 2 with `pending_implementation` because
the suites do not exist. It refuses to silently skip them. Planned tests must
use real PostgreSQL with restricted runtime and independent provisioning roles;
callback/order/rollback tests need deterministic barriers and reconnect checks.
Test names inventory coverage only; it does not prove the assertions or accept
storage/security behavior. Root must review the actual tests and receipts.

No independent reviewer has accepted the schema or implementation. Full product
scope, operational/provider qualification, native/physical final acceptance and
published separate-repository FieldLog dogfooding remain pending.
