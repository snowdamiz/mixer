#!/usr/bin/env python3
"""Check/seal exact immutable leaf-review evidence; no execution of product code."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DOC = ROOT / "docs/android-private-owner-leaf-review.md"
MANIFEST = HERE / "manifest.json"
SIDECAR = HERE / "manifest.sha256"
RESULT = HERE / "seal-result.json"
EXCLUDED = {MANIFEST, SIDECAR, RESULT}
PINS = {
    1: "f4633dab3fd25713feaf93162b5ffb888b277108683781b7b118a010cf14b79e",
    2: "d58e1c1b8ca942089603c1e5d3a63bec93198935f256e7ab6f92e2b7a31a70f9",
    3: "d772bfae9febf9106b1338be259cb026e4293d8e287fa792939340754ccdda38",
}


def record(p):
    b = p.read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


def load(p):
    return json.loads(p.read_text())


def verify_content():
    assertions = 0
    def check(condition, message):
        nonlocal assertions
        assertions += 1
        if not condition:
            raise AssertionError(message)
    manifests = []
    for version, pin in PINS.items():
        name = "leaf-manifest.json" if version == 1 else f"leaf-manifest-{version}.json"
        path = HERE / "admission" / name
        check(record(path)["sha256"] == pin, "exact admitted manifest")
        m = load(path); manifests.append(m)
        base = HERE if version == 1 else HERE / f"delta-{version}"
        actual = {str(p.relative_to(base/"inputs")) for p in (base/"inputs").rglob("*") if p.is_file()}
        check(actual == set(m["files"]), "exact 74-source closure")
        check(len(actual) == 74 and len(m["substituteFQCNs"]) == 73, "73 FQCN plus probe")
        for name, expected in m["files"].items():
            check(record(base/"inputs"/name) == expected, "exact source bytes " + name)
        result = load(HERE/"results"/f"leaf-{version}"/"result.json")
        check(result["compile"] == 0 and result["compiled_scratch_absent"], "compile and cleanup")
        check(result["run"] == (1 if version == 2 else 0), "honest leaf run outcome")
        compiled = load(HERE/"results"/f"leaf-{version}"/"compiled-class-hashes.json")
        for subject in ("NativeOwnerV2", "OwnerLifecycleV2", "NativeCoordinatorV2", "NativeRenderer", "NativeEnvironmentV2",
                        "NativeAppearanceViewsV2", "InstalledAppearanceV2", "UiPacket", "Json", "AppearanceDescriptorV2",
                        "AppearanceGeometryV2", "AppearanceResolverV2", "AppearanceNativePathsV2", "AuthoredToggleInputV2"):
            check("dev/mixer/android/"+subject+".class" not in compiled, "no actual product subject compiled")
    probe = "native/android/tests/NativeOwnerV2ConcreteHostLeaves/dev/mixer/android/ConcreteHostProbe.java"
    for name in manifests[0]["files"]:
        if name != probe:
            check(manifests[0]["files"][name] == manifests[1]["files"][name] == manifests[2]["files"][name], "73 unchanged bodies")
    old = (HERE/"delta-2/inputs"/probe).read_text(); current = (HERE/"delta-3/inputs"/probe).read_text()
    check(current == old.replace("StackWalker.getInstance();", "StackWalker.getInstance(StackWalker.Option.RETAIN_CLASS_REFERENCE);"), "sole exact probe3 fix")
    for version, count in [(1,80),(3,82)]:
        raw=(HERE/"results"/f"leaf-{version}"/"03-run.stdout").read_text().splitlines()
        trace, summary = map(json.loads, raw)
        check(trace["syntheticOnly"] and trace["sameLine"] == 315 and trace["firstBCI"] == 3 and trace["secondBCI"] == 9, "same-line witness")
        check(trace["descriptor"] == "(Landroid/graphics/Paint;)V" and trace["probeRetainsStrongSite"] == (version == 3), "strong descriptor identity")
        check(summary["controls"] == 12 and summary["assertions"] == count and summary["productTests"] == 0, "leaf-only exact controls")
    failure=(HERE/"results/leaf-2/03-run.stderr").read_text()
    check("UnsupportedOperationException: No access to RETAIN_CLASS_REFERENCE" in failure and "ConcreteHostProbe.java:35" in failure, "preserved leaf2 rejection")
    audit=load(HERE/"per-file-audit.json")
    check(len(audit["rows"]) == 74 and all(x["independent_complete_body_inspection"] for x in audit["rows"]), "complete body audit")
    check(all(not x["authority_or_encoded_product_outcome_found"] for x in audit["rows"]), "bounded noauthority opinion")
    receipt=load(HERE/"receipt.json")
    check(receipt["product_subjects_compiled_or_executed"] == 0 and not receipt["product_candidate_or_producer_tests_or_parent_evidence_access"], "scope attestation")
    check(receipt["leaf3"]["remaining_leaf_only_blockers"] == [], "recommendation scope")
    check(not (HERE/"scratch").exists(), "no owned scratch remains")
    for p in (HERE/"results").rglob("*.command.json"):
        command=load(p)
        check(command["forced_termination"] is None, "command bounded completion")
        check(command["limits"]["owned_children"] == 1 and command["limits"]["wall_seconds"] == 120, "child/time limits")
        if "--release" in command["argv"]:
            check(command["argv"][command["argv"].index("--release")+1] == "17", "actual Java17 target")
            check(all(x in command["argv"] for x in ["-Xlint:all","-Werror","-proc:none","-sourcepath","-classpath"]), "strict explicit compile")
    preaccess=ROOT/"verification/android-private-owner-independent-review/preaccess/manifest.json"
    check(record(preaccess)["sha256"] == "3d9100d342756d902152a6e786ec0e2a8ae1cd63d3ca79dde68f56ce3c7a390b", "preaccess manifest untouched")
    prior=load(preaccess)
    priorplan=ROOT/"docs/android-private-owner-implementation-review-plan.md"
    check(record(priorplan) == prior["files"][str(priorplan.relative_to(ROOT))], "sealed preaccess plan untouched")
    check(DOC.is_file(), "owned final review document")
    return assertions


def members():
    return sorted([p for p in HERE.rglob("*") if p.is_file() and p not in EXCLUDED] + [DOC])


def main():
    assertions=verify_content()
    if sys.argv[1:] == ["--seal"]:
        if any(p.exists() for p in EXCLUDED):
            raise SystemExit("refuse to overwrite sealed leaf review")
        files={str(p.relative_to(ROOT)):record(p) for p in members()}
        MANIFEST.write_text(json.dumps(dict(schema=1, scope="mechanical leaf-only independent review; zero product tests",
            members=len(files), bytes=sum(x["bytes"] for x in files.values()), files=files,
            excluded_metadata=["manifest.json","manifest.sha256","seal-result.json"],
            external_owned_document=str(DOC.relative_to(ROOT)),
            command=["python3","-B","verification/android-private-owner-independent-review/leaf-review-1/verify_and_seal.py","--seal"],
            python=sys.version),indent=2,sort_keys=True)+"\n")
        SIDECAR.write_text(record(MANIFEST)["sha256"]+"  manifest.json\n")
    elif sys.argv[1:] not in (["--check"], ["--content"]):
        raise SystemExit("expected --content, --seal or --check")
    if sys.argv[1:] == ["--content"]:
        print(json.dumps(dict(status="passed-leaf-evidence-custody-only",assertions=assertions,product_tests=0)))
        return
    manifest=load(MANIFEST);actual={str(p.relative_to(ROOT)):record(p) for p in members()}
    if actual != manifest["files"] or SIDECAR.read_text() != record(MANIFEST)["sha256"]+"  manifest.json\n":
        raise SystemExit("exact leaf-review closure or bytes changed")
    result=dict(status="sealed-exact-leaf-review-verified",manifest_sha256=record(MANIFEST)["sha256"],
                members=len(actual),bytes=sum(x["bytes"] for x in actual.values()),assertions=assertions,
                recommendation="root-admit-exact-leaf3-for-bounded-mechanical-reuse",product_tests=0)
    if sys.argv[1:] == ["--seal"]:
        RESULT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    elif load(RESULT) != result:
        raise SystemExit("deterministic seal-result sidecar mismatch")
    print(json.dumps(result,sort_keys=True))


if __name__ == "__main__":
    main()
