#!/usr/bin/env python3
"""Create the sole lifecycle fixture overlay; never execute product code."""
from offline_guard import install
install()

import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
UPSTREAM = ROOT / "verification/swift-dense512-product-integration"
REL = "src/experimental_swift_reactor/lifecycle_tests.rs"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def row(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": sha(raw)}


def closure(rows):
    return sha("".join(n + "\0" + rows[n]["sha256"] + "\n" for n in sorted(rows)).encode())


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


REPLACEMENTS = [
    (
        "// and eight charged semantic cells for each of 512 scan-plan entries.\n    assert_eq!(start.cache_work, 29 + 64 + 512 + 192 + 512 * 8);",
        "// and eight charged semantic cells for each of 512 scan-plan entries.\n    // Publishing the initialized free-pin bitmap costs one additional credit.\n    assert_eq!(start.cache_work, 29 + 64 + 1 + 512 + 192 + 512 * 8);",
    ),
    (
        "// Cold cost adds 13 actual probe/publication credits to the original\n    // 108 + pin records + 2*encoded body bytes + 3*instructions.\n    // Init35: B14/I6/P1; corpus62: B7/I3/P1; callee36: B19/I9/P2.",
        "// Cold cost includes 13 probe/publication credits and five credits for\n    // successful bitmap pin selection: 108 + 5 + 2*body bytes + 3*instructions + 13.\n    // Init35: B14/I6; corpus62: B7/I3; callee36: B19/I9.",
    ),
    ("108 + 1 + 2 * 14 + 3 * 6 + 13", "108 + 5 + 2 * 14 + 3 * 6 + 13"),
    ("assert_eq!(initialized.cache_work, 5_061);", "assert_eq!(initialized.cache_work, 5_066);"),
    (
        "(108 + 1 + 2 * 7 + 3 * 3 + 13) + (108 + 2 + 2 * 19 + 3 * 9 + 13)",
        "(108 + 5 + 2 * 7 + 3 * 3 + 13) + (108 + 5 + 2 * 19 + 3 * 9 + 13)",
    ),
    ("assert_eq!(first.cache_work, 5_394);", "assert_eq!(first.cache_work, 5_406);"),
    (
        "// Lookup + pin-record scan + checked index chain: outer1+1+6, nested1+2+6.",
        "// Lookup + bitmap pin selection + checked index chain: both 1+5+6.",
    ),
    ("(1 + 1 + 6) + (1 + 2 + 6)", "(1 + 5 + 6) + (1 + 5 + 6)"),
    ("assert_eq!(second.cache_work, 5_411);", "assert_eq!(second.cache_work, 5_430);"),
    (
        "// Constructor 4,893; cold no-op init B2/I1:108+1+4+3+13=129.",
        "// Constructor 4,894; cold no-op init B2/I1:108+5+4+3+13=133.",
    ),
    ("cache_work: 5_022,", "cache_work: 5_027,"),
    ("assert_eq!(observed(&o).cache_work, 5_022);", "assert_eq!(observed(&o).cache_work, 5_027);"),
    ("assert_eq!(f.at_failure.cache_work, 5_022);", "assert_eq!(f.at_failure.cache_work, 5_027);"),
]


def corrected(text):
    for old, new in REPLACEMENTS:
        if text.count(old) != 1:
            raise AssertionError("Exact baseline replacement count: " + old)
        text = text.replace(old, new, 1)
    return text


def main():
    upstream = json.loads((UPSTREAM / "manifest.json").read_text())
    baseline = ROOT / "vm" / REL
    assert row(baseline) == upstream["baselineFiles"][REL] == upstream["candidateFiles"][REL]
    original = baseline.read_text()
    result = corrected(original)
    dest = HERE / "candidate/vm" / REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(result)
    before = HERE / "baseline/vm" / REL
    before.parent.mkdir(parents=True, exist_ok=True)
    before.write_text(original)
    (HERE / "lifecycle-tests.diff").write_text("".join(difflib.unified_diff(
        original.splitlines(keepends=True), result.splitlines(keepends=True),
        fromfile="baseline/vm/" + REL, tofile="candidate/vm/" + REL,
    )))
    files = dict(upstream["candidateFiles"])
    files[REL] = row(dest)
    overlays = list(upstream["overlayPaths"]) + [REL]
    provenance = {
        n: ("verification/swift-dense512-product-integration/candidate/vm/" + n
            if n in upstream["overlayPaths"] else "vm/" + n)
        for n in files
    }
    provenance[REL] = "verification/swift-pin-bitmap-lifecycle-correction/candidate/vm/" + REL
    save(HERE / "manifest.json", {
        "schema": 1,
        "scope": "One test-only overlay on the frozen canonical-limit bitmap candidate; source review only",
        "baselineCommitParentSupplied": "c7648ab4",
        "baselineGitTreeParentSupplied": "3143f5e45b535d525c90cf0df6e9e884c225646c",
        "baselineTreeSHA256": upstream["baselineTreeSHA256"],
        "priorCandidateTreeSHA256": upstream["candidateTreeSHA256"],
        "candidateTreeSHA256": closure(files),
        "treeDigestFormat": "sha256(sorted(path + NUL + fileSHA256 + LF))",
        "baselineFiles": upstream["baselineFiles"],
        "priorCandidateFiles": upstream["candidateFiles"],
        "candidateFiles": files,
        "overlayPaths": overlays,
        "newOverlayPaths": [REL],
        "materializationPaths": provenance,
        "canonicalProductFilesEdited": False,
        "priorFrozenPacketsEdited": False,
        "hostHarnessChanged": False,
        "newDispatchSelected": False,
    })
    seals = {}
    for packet, expected in [
        ("swift-dense512-product-integration", "290909956b188ed46c73c2c73541c8ed60a80788f0d51f9adbca0940579a54f2"),
        ("swift-pin-bitmap-independent", "84b2cc15c97f951d850904a733ec747fbbb0b17ee23fe8f0b19a8da285c5dfaa"),
        ("swift-pin-bitmap-host-binding-correction", "f44236c30b0a789b86171d864cf997537d7055a4a32543243854871081b2ab3f"),
    ]:
        path = ROOT / "verification" / packet / "seal.json"
        assert row(path)["sha256"] == expected
        seals[str(path.relative_to(ROOT))] = row(path)
    local = ROOT / "verification/reviewed-host-slice-actual-results/local"
    actual = local / "pin-bitmap-extract/_temp/swift-pin-bitmap-v1-evidence"
    actual_files = [local / "pin-bitmap.zip", actual / "source-manifest.json",
                    actual / "commands/cargo-5.stdout", actual / "commands/cargo-5.stderr",
                    actual / "commands/compiler-identity.stdout"]
    save(HERE / "baseline-bindings.json", {
        "schema": 1, "frozenSeals": seals,
        "actualArtifact": {"runID": 40806119805, "artifactID": 12868935321,
                           "sha256": "1452097cd405aa96a1facdd53bbd3fcf8a83affb5bb1b5735f35277e21ad1d26"},
        "actualLocalOnlyFiles": {str(p.relative_to(ROOT)): row(p) for p in actual_files},
        "baselineLifecycle": row(baseline),
        "sourceDiagnosisInputs": {
            str(p.relative_to(ROOT)): row(p) for p in [
                ROOT / "vm/src/experimental_swift_reactor/control.rs",
                ROOT / "vm/src/experimental_swift_reactor/lifecycle.rs",
                ROOT / "vm/src/experimental_swift_reactor/frame_operations.rs",
                UPSTREAM / "candidate/vm/src/experimental_swift_reactor/cache.rs",
                UPSTREAM / "candidate/vm/src/experimental/cache/borrowed.rs",
                ROOT / "verification/swift-pin-bitmap-host-binding-correction/admit.py",
                UPSTREAM / "host-plan.json",
            ]
        },
        "actualCorrectedRustResults": "pending",
    })
    print(json.dumps({"candidateTreeSHA256": closure(files), "newOverlayPaths": [REL], "sourceMembers": len(files)}))


if __name__ == "__main__":
    main()
