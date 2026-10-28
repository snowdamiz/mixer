# Packet membership amendment

The original freeze.json and audit.json remain immutable, as do all original
packet files. The original producer freeze is
85f2376f7f8ba7628890336f08e2dc59935dce922da2f8f908b940e08452f752.
Its 28 listed files retain correct hashes, but its membership was incomplete.
The freeze builder excluded every basename freeze.json, omitting both the
intended terminal seal and this copied upstream seal:

inputs/verification/console-dispatcher-default-authority-slice/freeze.json
SHA-256 3700d4fd7f89a52de22967e510289745f8ed8aad3bbf7ff7e0a0c2fa88a9fa33

The preserved verify_packet.py repeats the same basename exclusion in its
actual_paths inventory. Its evidence loop separately checked the copied upstream
seal through reviewed-evidence.json, but that indirect hash check did not make
the terminal file-membership assertion complete. Its positive audit is therefore
limited by this producer verifier defect; use the amendment verifier for closure.

membership-amendment.json is the new terminal membership seal. It lists every
file below this packet, including the original terminal seal, the copied upstream
seal, this explanation, the independent membership verifier, and its preparation
audit. The sole exclusion is the exact packet-relative path
membership-amendment.json itself. No basename filter is used.

Run:

    python3 -B verification/console-key-owner-lifecycle-contract/verify_membership_amendment.py

That read-only check requires exact file-set equality, validates every listed
byte/hash, rejects duplicate/escaping paths and symlinks, checks the aggregate
manifest digest, and verifies the original 30-file packet remains unchanged.
The preparation audit precedes the amendment seal and claims only baseline
integrity; the final verifier output establishes closed amendment membership.

Root also reported an initial root-side path-resolution mistake selecting the
repository README.md instead of the packet README.md. Corrected packet-relative
hashing passed all 28 original entries. That reader error is separate from the
producer membership defect fixed here. No product source, compiler/runtime test,
original evidence, or lifecycle-contract conclusion changes in this amendment.
