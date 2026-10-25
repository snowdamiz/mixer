# Digest-addressed customer upload

The additive `CustomerArtifacts.upload_at/6` API checks the expected route
digest against the admitted signed artifact before opening the owning database
transaction. Existing `upload/5` behavior is preserved. The HTTP adapter can
therefore distinguish `digest_mismatch` and `artifact_invalid` without learning
that the URL was wrong after committing a write.

The focused collector runs the existing public-facade suite plus three cases:
route mismatch before creation and on retry, invalid expected digests without a
fallback, and scope admission before artifact error classification. It records
table/head counts alongside successful first-write/retry/new-key results.

This is local PostgreSQL application evidence. HTTP, default identity-owner,
real socket and provider behavior require separate receipts. No frozen lane,
shared harness main, UI, capture, native instance or external provider is used.
