# Browser session storage proposal evidence

This packet records source review and a proposed implementation contract. It
contains no product implementation, simulated successful login, cryptographic
qualification, SQL migration or executed lifecycle integration tests.

Root agreed the migration reservation, separate lifecycle role/pool,
replacement-start behavior and same-database transaction on 2026-10-25.
Product implementation remains separately assigned and pending.
See `docs/hosted-browser-session-storage-contract.md` for exact inputs, outputs,
locks, failure behavior, encryption, role topology and implementation gates.

`required-cases.json` lists required real implementation checks. Every case is
pending. No runner is provided because re-executing a model or checking prose
cannot establish the transaction/role/cryptographic boundary.

`receipt.json` binds the reviewed source files and tool observations. The source
revision is context only: parallel lanes can change other files after it was
observed. The SHA-256 digest binds only the listed bytes, not the whole checkout.
