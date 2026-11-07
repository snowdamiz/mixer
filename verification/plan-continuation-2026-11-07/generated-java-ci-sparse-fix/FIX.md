P1 correction is ready for fresh review and parent adoption. No canonical job was edited or dispatched.

The candidate now uses actions/checkout@v4 with non-cone sparse patterns for cli, sdk, updates, native/android, scripts/ci and its own candidate namespace. No filter override is set: the reviewed official checkout v4 sparse path retains blob:none fetching. This work performs no fetch and creates no full checkout. Git's real non-cone rule matcher validates the patterns extracted from the actual proposal.

The selected tracked closure contains 471 regular files / 4,984,927 bytes. A disposable selected-only filesystem projection also includes the complete candidate. It reproduces all 101 canonical owning inputs with SHA256 53ad5501dcaa0168ec8196c8816d07a246e6b04bcd0160edadd22ecafd4ff815. This includes all package source/resources/manifests/lockfiles, dependency verifier, adapter inputs and control-test metadata. Remote SwiftPM dependencies remain pinned runtime downloads; no remote dependency body was downloaded here.

The unchanged original 22 controls pass in that projection normally and under -O. Twelve new controls pass in both modes, covering the actual proposal, all six directory omissions, exclusion boundaries, cone/filter/full-checkout regressions, Git failure/timeout/bounds, source omissions/digest change and disk admission/receipt persistence. Three additional filesystem controls in the projection refuse actual missing manifests, a missing dependency verifier and changed manifest bytes. The sealed reviewer's two fake-child custody/failure probes also pass in both modes, replayed verbatim from a copy in this new evidence directory. The original review directory and original candidate receipt are preserved byte-for-byte. The latter describes the earlier candidate; receipt.json in this directory is the current receipt.

Bootstrap keeps the 12 GiB minimum and now persists the actual initial free-byte observation, timestamp, observed path, threshold and admission result before any tool commands or downloads. It also refuses any owning-input count/digest differing from this reviewed pair8 closure before native execution. This candidate intentionally remains tied to pair8; a later pair9 adoption needs separate review.

Reproduce with:

    python3 -I -B -S verification/plan-continuation-2026-11-07/generated-java-ci-sparse-fix/verify_sparse_fix.py

All writes are confined to the candidate namespace and this new evidence namespace. The selected-only disposable projection and test scratch were removed. Commands, input identities, selected-tree identities, before/after hashes and changed paths are retained. Concurrent modifications to PLAN.md, STATUS.md, gates/ga.json and work-graph.json were observed and left untouched.

No hosted execution, initial hosted free-space measurement, package expansion envelope or Swift/Java compilation is established. This Mac's actual free-space observation is local evidence only. First ordinary hosted execution must still validate disk/time use after parent review/adoption. No download, SDK manager, compiler, JVM, native UI/device action, historical process probe/signal, dispatch, child delegation, commit or push occurred. Historical PGIDs 20745/20770/20780/20817/20842/20851/20866, FieldLog PGID2424/PID2621, held v5 startup and frozen hosted lanes remain untouched.
