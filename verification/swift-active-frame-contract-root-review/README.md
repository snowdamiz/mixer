# Private active-frame contract root acceptance

`acceptance.json` authorizes the complete private entry/return/drain implementation.
It does not accept an implementation, actual binding completeness, frame execution,
native behavior, release authority, or a GA gate.

Root checks 1,625 bindings across the amended producer packet, independent review,
and its own replay. The producer performed 81 commands; independent review added
two fresh host compilations and sixteen exact metadata replays. Root extracted
the compact archive, ran sixteen metadata-only binaries and inspected eight ABI
dylibs with `nm`. No guest function, frame algorithm, app or simulator was run.

The initial map omitted distinct pre-entry snapshots and exact ticket-layout call
positions. The accepted amendment adds those positively. Original guard layout,
Frozen methods/reservation and the existing value scratch remain unchanged. The
new frame envelope is 360,352 bytes on this host, including a separately admitted
full 119,576-byte nested value-operation component. Actual implementation may add
positive positions; it may not consume old scratch, padding or occupied roles.

Check retained evidence without depending on current product files or Cargo targets:

```
python3 -B verification/swift-active-frame-contract-root-review/check_saved.py
python3 -B verification/swift-active-frame-contract-review/verify_saved.py
```

`replay.py <producer-seal-sha256>` reproduces the root host artifact executions
and deliberately checks the product tree at the time of contract review. Later
authorized implementation changes are expected to differ from that baseline;
the immutable archive and saved receipts preserve the reviewed source. The only
baseline drift at acceptance was the independently accepted test-observer repair.

All AF01–AF22 execution cases and actual-source accounting review remain required.
The native testing pause and all product/dogfood gates remain unchanged.
