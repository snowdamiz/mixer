# HTTP/2 formatted source successor

This minimal successor retains the exact root-applied formatter output for the
same two-file implementation. V1 and its independent source review remain
unchanged. Five methods and seven finite subcases retain their reviewed scope.

The fixture changed from SHA256
`965c38f6dac459de2baaf3fee98c66ee663a013ccc9401d14d233fbab27794af`
to `c0ba4561576060c525e586414fcfeacc88cfa19b14607d4f13dffaca32da7f4e`.
Its delta is five blank lines and parentheses around the subtraction used in
the read-interval check. The test is unchanged at
`4656e1f05e20ddfe8767be837a38d8323313efd7ef77efa7176a748c518c8ce8`.
`formatting-only.patch` records that narrow delta; `two-file.patch` and `source/`
record the exact new-file delivery bytes.

Root's retained `verification/hosted-http2-format-root-1/receipt.json` reports
one Elixir 1.20.4 Code formatter operation, 0.228701 seconds, normalized AST
equivalence for both files, exit zero, child reaped, owned group absent and
scratch removed. This preparation only hash checks that evidence and copies its
exact outputs. It does not repeat parsing, formatting or process observations.
No compiler, test or listener ran in the formatter operation. The ordinary CI
format check for the delivered tree remains pending alongside compilation/tests.

The 28 unique V1 current-input pins have exactly two authorized changes: the
fixture formatting above and the separately owned collector edit in
`hosted/scripts/test-local.py`, now SHA256
`78292dbf027bff4fae67d638fec9504c042cbeac39b6bca40e38321178bb5951`.
That collector's independent review is pending separately. This packet records
its current byte pin and authorization; it does not review or accept its
behavior and does not include the collector in the two-file patch. The other
26 pins are unchanged, including all protected files and canonical dependency
files. Unexpected drift fails the preparation.

The observed checkout revision is `c51f67c5c51b4172d8cae03b966b43f891bddb2d`.
The intended next steps are final formatting-delta review, separate collector
review, then root's coherent ordinary remote delivery through the existing
Phoenix workflow. Its existing runner still supplies format, compile and
`mix test --warnings-as-errors --seed 0 --trace`. Acceptance requires green
enclosing tests/CI as well as all seven reviewed wire receipts and cleanup;
individual receipt lines alone do not qualify a case.

No implementation behavior, canonical source, dependencies, workflow, store or
lifecycle source was changed by this successor preparation. It used bounded
offline Python file/hash/diff bookkeeping only. There was no further formatter,
Elixir/Mix/compiler/test/listener/network/native/capture/process probe. Both
HTTP/2 wire qualifications remain pending. The shared 25-second clock remains
an admission/cooperative-wait deadline, with a separate 26-second per-test
failure guard; it is not a hard module wall-time claim. No broader advisory,
memory/backpressure, provider/production, device or GA acceptance is inferred.
