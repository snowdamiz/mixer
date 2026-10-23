# Independent declared-input capture review

Reviewed original `c01e8016880dcbf1c15010142ad856327d7ba0f8` and the diagnostic fix `629ee0f725ae407fc1967af150d5ce38f2c009cc`. Reviewer selection: `gpt-6.1-sol`, `xhigh`. All implementation files were read-only. The frozen export includes runtime-identity, updates and the valid synthetic descriptor seed; original private fixtures and adversarial mutations are authored in this review lane.

Original source digest: `92371abbf90d0825003ee786ee8883cd105ac253abfff621a35454b2bcbb2f83`. Final source digest: `0e93029747dc12bea68a543782b30c415700b7785c91f7f16301c86bdede3a5c`. Each receipt enumerates all 48 exported file hashes, archive identity, tool identity, commands, logs and test-source hashes. The actual public Swift mixer-identity CLI was reused from root's frozen c01 export, with SHA-256 `3770e3feae9cf9fbd6ef3dd3750e852bdcbf9796b686b6488b8417d3d886619b`; its source-build receipt is separately pinned. The two revisions differ only in capture.py and its tests, so the descriptor validator source remains identical. This is a trusted real CLI provenance reference, not an independent binary build attestation.

The initial run passed 17 characterization functions in each of normal and optimized Python modes. It confirmed one low-severity diagnostic defect: a 5,000-digit invalid schema number raised plain ValueError from Python's integer conversion limit, escaped the decoder wrapper and printed a traceback. It still exited1 and created no output. Root independently identified this issue and fixed it in 629ee0f; this review did not edit implementation. The final run passed 20 functions per mode, including an explicit no-traceback assertion. Historical initial runner/test source copies and logs are preserved with the pre-fix receipt, so the initial characterization is not silently rewritten as the final regression check. There is no remaining confirmed blocking defect within this review's scope.

The original probes exercise:

- Independently calculated raw-file, empty-collection and collection digests; only digest fields change; one source path is captured once and later source replacement/deletion cannot retarget the captured snapshot.
- Descriptor-relative directory pinning during a concurrent parent rename/symlink swap, a leaf replacement after open, and a symlink before leaf open. Opened original bytes are captured or the operation rejects; an external private witness never changes and its bytes never enter the object inventory.
- In-place source overwrite during a multi-chunk read, including restored mtime, rejects through changed inode metadata. FIFO/socket/directory/symlink source inputs reject without blocking; existing output files, directories and links are preserved.
- Actual 1MiB manifest and 128KiB descriptor exact/+1 boundaries; actual 4,096/4,097 declared entries; an oversized generated final manifest; and an actual 1GiB+1 sparse-length source rejected by the stat guard. The per-file/aggregate exact byte-stream boundaries are exercised with reduced constants and small files, including zero-byte files and their real SHA-256. No actual 1GiB/4GiB streaming or deployment memory/performance claim follows.
- Closed shapes, path/name limits, malformed/duplicate/escaped JSON fields, finite and unsupported values, expected fingerprint mismatch, consistent descriptor-policy rehash tampering, object/report/collection corruption and external object/report/descriptor symlinks.
- Abrupt process exit before inputs.json publication leaves an unverifiable partial directory. An injected sync failure removes the exclusively created private output. These are controlled process/error probes, not a power-loss filesystem qualification.
- All 128 dependencies plus 128 capabilities yield 655 independently enumerated digest bindings; omission rejects. UInt64.max and three exact Unicode export spellings survive capture without policy changes. The JSON helper's 30,000-node and 16-depth bounds pass at the boundary and reject at +1.

Reproduce the final review from this repository, while the pinned root CLI export remains available:

```sh
python3 -B verification/input-capture-review/run.py \
  --name FRESH_NAME --revision 629ee0f725ae407fc1967af150d5ce38f2c009cc \
  --expect-clean-diagnostic
```

Alternatively supply `--identity-tool /absolute/trusted/mixer-identity`; the actual binary hash is recorded and the caller remains responsible for that executable's trust. New runs create fresh private `.build/` source/fixture directories and evidence directories, and do not mutate reviewed implementation or existing snapshots. Normal and Python `-O` runs both use unittest assertions. Source archives are derived from Git commits and checked unchanged after tests.

This review qualifies declared-byte copying, bounded local input handling, manifest/object verification and the resolved error diagnostic on macOS arm64/Python3.14.8 using the pinned Swift CLI. It does not discover the complete native graph, establish compiler/SDK version truth, prove a build consumed the snapshot, sign/attest provenance, embed identity into a binary, establish same-user snapshot immutability, qualify physical devices, authorize a release, or close dogfood/GA gates. Slow/remote filesystem wall-clock bounds, full filesystem crash/power-loss testing and complete hostile-filesystem/security auditing remain outside the evidence.
