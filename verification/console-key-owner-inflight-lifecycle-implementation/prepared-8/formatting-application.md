# Exact formatter output application

The root-issued single-execution release bound formatting-plan.json SHA-256
6476cd142edd9c808d18e7d057af6ad6d201e8751f3447574ccc71ad49ace11c.
The retained receipt reports passed, no errors/signals, exact child 50285 reaped,
its process group absent, scratch removed and original input hashes unchanged.
The release file SHA-256 is
dd68817a7c2edae2cbeea819b615cde70cbcf4dd6c793a4b62b06063930b88e4.

Before applying bytes, both canonical inputs matched the released snapshots and
their source hashes in formatting.json. Both output basenames, byte counts and
SHA-256 values matched their exact source bindings. The format execution's seven
retained output files matched its complete expected membership. Each output's
non-whitespace bytes match its input; the complete source-only diff is retained.

KeyOwnerSupervisor stayed at 1,072 bytes, SHA-256
cdb7b901a8e521361e1578bf0b47ea521a31c61c681c27d1f164925081238ba2.
The new inflight lifecycle test changed from 23,116 to 24,825 bytes and now has
SHA-256 9a90b9aa33d0d3b4533023e033630568f926dd90b2f7850c660d322b8d7a74f2.
No manually authored product source change was mixed into this application.

prepared-1, its root release and executions/formatting-1 remain unchanged.
Candidate 2 separately freezes those references, formatted source and a
runtime-only runner. Its harness change requires exact phase/root output
membership and retains available JSON observations when another artifact is
missing. It changes no product method, test assertion, test count, compiler
diagnostic policy, TLS path, OpenSSL recipe or resource-gate expectation.

This step uses source reads, hashes and exact authorized byte writes only.
Production/test compilation and all nine methods remain unexecuted; formatting
does not accept the production exclusion, TLS lifecycle, KOL09 fault or GA gates.
