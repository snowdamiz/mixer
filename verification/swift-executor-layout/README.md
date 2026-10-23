# Swift executor layout prerequisite evidence

Run on the qualified Apple arm64 host:

```sh
python3 verification/swift-executor-layout/collect.py
python3 verification/swift-executor-layout/build_map.py
python3 verification/swift-executor-layout/seal.py
```

`collect.py` builds an ignored derived `tree/`, uses ignored `build/` for Cargo,
and never edits existing working VM files. `root-wiring.patch` is the exact
minimal root-owned integration proposal. `measurement-overlay.patch` additionally
contains a derived-only metadata export/example and probe module, which must
never become product API. The full pre-overlay input and post-overlay manifests
bind every copied file. Negative probes are an exact appended source snippet
or exact external example, with each command, source hash and required diagnostic
recorded. Their final derived files are restored before Clippy runs.

`receipt.json` records 41 commands, tool versions, all actual exit codes and log
hashes. Nonzero negative-probe exits are expected and checked for the intended
diagnostic. `layout-map.json` contains eight phase maps and separate non-test /
unit-instrumented layouts. `final-boundary-map.json` is review input with an
explicit unresolved foundation accounting dependency. `regression-scope.json`
lists the actual suite scope and omissions. `source-freeze.json` binds the code,
root wiring, metadata overlay, scripts, maps and receipts used for this lane.

The four new production files are compiling staged types and borrow/cleanup
helper boundaries only. There is no constructor or interpreter algorithm.
Named phase inventories are chosen prerequisite budgets; their eventual
algorithm-to-binding attribution remains an executor acceptance requirement.
The two additional final-boundary supplement types are incomplete starter
probes. A successful behavior test is not acceptance of those supplements.

No full target instantiate/initialize/invoke, public execution, device discovery
or run, published FieldLog consumption, release/store/customer/GA acceptance,
commit or push occurs in this lane. Historical artifacts remain sealed.
