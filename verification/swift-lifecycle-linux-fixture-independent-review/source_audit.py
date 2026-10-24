#!/usr/bin/env python3
"""Audit the final producer seal, then copy only exact recorded VM inputs."""
import difflib
import hashlib
import json
import platform
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRODUCER = HERE.parent / "swift-lifecycle-linux-fixture-repair"
HISTORICAL = HERE.parent / "swift-reactor-lifecycle-remaining-matrix"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    seal = json.loads((PRODUCER / "seal.json").read_text())
    assert "files" in seal
    errors = []
    checked = 0
    for name, digest in seal["files"].items():
        checked += 1
        if sha(PRODUCER / name) != digest:
            errors.append(name)
    for name, digest in seal.get("externalFiles", {}).items():
        checked += 1
        if sha(ROOT / name) != digest:
            errors.append(name)
    assert not errors, errors
    producer_source = json.loads((PRODUCER / "source.json").read_text())
    baseline = json.loads((PRODUCER / "baseline-manifest.json").read_text())
    historical = json.loads((HISTORICAL / "candidate-manifest.json").read_text())
    candidate = json.loads((PRODUCER / "candidate-manifest.json").read_text())
    assert baseline == historical
    assert set(candidate) == set(baseline)
    assert len(candidate) == 132
    changed = sorted(name for name in candidate if candidate[name] != baseline[name])
    assert changed == ["src/experimental_swift_reactor/control.rs", "src/experimental_swift_reactor/lifecycle_tests.rs"]
    for name, digest in candidate.items():
        assert sha(PRODUCER / "candidate" / name) == digest, name
        assert sha(ROOT / "vm" / name) == digest, name
    control_name, tests_name = changed
    helper = (PRODUCER / "test-only-helper.txt").read_text()
    original_control = (PRODUCER / "baseline" / control_name).read_text()
    final_control = (PRODUCER / "candidate" / control_name).read_text()
    assert final_control.count(helper) == 1
    assert final_control.replace(helper, "") == original_control
    assert final_control.index("#[cfg(test)]\nimpl RuntimeControl {") < final_control.index(helper) < final_control.index("/// The actual proof moves")
    old_tests = (PRODUCER / "baseline" / tests_name).read_text()
    new_tests = (PRODUCER / "candidate" / tests_name).read_text()
    identities = lambda text: sorted(re.findall(r"#\[test\]\s*fn\s+(swift_lifecycle_\w+)\s*\(", text))
    assert len(identities(new_tests)) == 49
    assert identities(old_tests) == identities(new_tests)
    assert '#[cfg(test)]\n#[path = "lifecycle_tests.rs"]\nmod tests;' in (PRODUCER / "candidate/src/experimental_swift_reactor/lifecycle.rs").read_text()
    independent_delta = "".join("".join(difflib.unified_diff((PRODUCER / "baseline" / name).read_text().splitlines(keepends=True), (PRODUCER / "candidate" / name).read_text().splitlines(keepends=True), fromfile="baseline/" + name, tofile="candidate/" + name)) for name in changed)
    (HERE / "independently-recomputed.patch").write_text(independent_delta)
    (HERE / "exact-helper.txt").write_text(helper)
    save(HERE / "candidate-manifest.json", candidate)
    save(HERE / "test-identities.json", identities(new_tests))
    save(HERE / "host.json", {"platform": platform.platform(), "machine": platform.machine(), "system": platform.system(), "python": platform.python_version()})
    row = {"schema": "mixer.swift-lifecycle.linux-fixture.independent-source-audit.1", "sourceRevisionContext": producer_source["revision"], "producerSealSHA256": sha(PRODUCER / "seal.json"), "producerSealedFilesChecked": checked, "producerSealMismatches": errors, "sourceFiles": len(candidate), "sourceClosureSHA256": sha(HERE / "candidate-manifest.json"), "changedFiles": changed, "productionControlAfterRemovingExactCfgTestHelperMatchesBaseline": True, "other130FilesMatchAcceptedBaseline": True, "all49IdentitiesPreserved": True, "helperInsideExistingCfgTestImpl": True, "lifecycleTestsModuleIsCfgTestOnly": True, "liveMatchesFinalProducerSource": True, "ordinaryBuildProbePlanned": True, "independentNoExpiryControlPlanned": True}
    save(HERE / "source-review.json", row)
    source = HERE / "source"
    assert not source.exists()
    for name in candidate:
        destination = source / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PRODUCER / "candidate" / name, destination)
    assert {name: sha(source / name) for name in candidate} == candidate
    print(json.dumps(row, indent=2, sort_keys=True))
