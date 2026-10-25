#!/usr/bin/env python3
"""Read-only sealed artifact verifier. Prints JSON; never builds or extracts."""
import collections
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import tarfile

B = Path(__file__).resolve().parent
R = B.parents[1]
O = B / "attempt-1"
sha = lambda raw: hashlib.sha256(raw).hexdigest()
canonical = lambda value: (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def binding(p):
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink(), p
    raw = p.read_bytes()
    return dict(kind="file", mode=stat.S_IMODE(s.st_mode), bytes=len(raw), sha256=sha(raw))


def safe(n):
    p = PurePosixPath(n)
    assert n and not p.is_absolute() and ".." not in p.parts and str(p) == n


def payload(raw):
    out = {}
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as t:
        for m in t:
            safe(m.name)
            assert m.name not in seen and (m.isfile() or m.isdir()), m.name
            seen.add(m.name)
            if m.isfile():
                out[m.name] = (t.extractfile(m).read(), m.mode)
    assert not any(str(PurePosixPath(n).parent) in out for n in out)
    return out


def rows(values):
    return {n: dict(kind="file", mode=m, bytes=len(b), sha256=sha(b)) for n, (b, m) in sorted(values.items())}


def load(p):
    return json.loads(p.read_bytes())


def warning_messages(raw):
    return [s.split("warning:", 1)[1].strip() for s in raw.decode().splitlines() if "warning:" in s]


def verify():
    hraw = (B / "handoff.json").read_bytes()
    seal = sha(hraw)
    assert seal == (B / "handoff.sha256").read_text().strip()
    handoff = json.loads(hraw)
    assert not handoff["nativeExecuted"] and not handoff["nativeExecutionSelected"] and not handoff["gaAccepted"]
    for n, expected in handoff["members"].items():
        safe(n)
        assert binding(R / n) == expected, n
    actual = {str(p.relative_to(R)) for p in B.rglob("*") if p.is_file() and p not in [B / "handoff.json", B / "handoff.sha256"]}
    expected = set(handoff["members"]) - {"docs/apple-settings-fixed-chunk-native-build.md"}
    assert actual == expected, (actual - expected, expected - actual)
    assert not (O / "owned-build").exists()
    inputs = load(O / "input-bindings.json")
    assert inputs["controllerSourceRevision"] == "be472ce6424a691de5673e3438d2768264827d23"
    for n, expected_sha in inputs["pins"].items():
        assert binding(R / n)["sha256"] == expected_sha, n
    for lane, count in inputs["handoffMembersVerified"].items():
        members = load(R / lane / "handoff.json")["members"]
        assert len(members) == count
        for n, expected_row in members.items():
            safe(n)
            observed = binding(R / n)
            assert all(observed[k] == v for k, v in expected_row.items()), n
    selection = load(R / "verification/apple-settings-fixed-chunk-root-review/acceptance.json")
    assert selection["freshGenericRunnerBuildSelected"] and selection["sourceAndHostAccepted"]
    assert not selection["nativeExecutionSelected"] and not selection["gaAccepted"]
    source = load(O / "source-manifest.json")
    source_values = payload((O / "accepted-sources.tar.gz").read_bytes())
    assert rows(source_values) == source["sources"] and len(source_values) == 40
    assert binding(O / "accepted-sources.tar.gz") == source["archive"]
    assert sha(canonical(source["sources"])) == source["sourceTreeSHA256"]
    package = payload((R / "verification/apple-settings-fixed-chunk-implementation/review-source-package.tar.gz").read_bytes())
    assert len(package) == 97
    reviewed = {n.removeprefix("package/sources/"): v for n, v in package.items() if n.startswith("package/sources/accepted/")}
    assert source_values == reviewed
    prior_values = payload((R / "verification/apple-settings-instrumented-native-build/attempt-1/accepted-sources.tar.gz").read_bytes())
    assert set(source_values) == set(prior_values)
    changed = [n for n in sorted(source_values) if source_values[n] != prior_values[n]]
    assert changed == source["changedFromPriorCompileClosure"] == ["accepted/harness/UITests/ToggleUITests.swift"]
    four = {PurePosixPath(n).name: sha(b) for n, (b, _) in source_values.items() if n.startswith("accepted/harness/UITests/")}
    typecheck = load(R / "verification/apple-settings-fixed-chunk-review/typecheck.json")
    assert len(four) == 4 and four == source["exactFourSwiftFiles"] == typecheck["exactSourceHashes"]
    products = load(O / "product-manifest.json")
    product_values = payload((O / "products.tar.gz").read_bytes())
    assert rows(product_values) == products["products"] and len(product_values) == 55
    assert binding(O / "products.tar.gz") == products["archive"]
    assert sha(canonical(products["products"])) == products["productTreeSHA256"]
    app = {n: v for n, v in product_values.items() if n.startswith("MixerToggleDiagnostics.app/")}
    assert len(app) == 13 and rows(app) == products["originalApplicationFiles"]
    with tarfile.open(R / "verification/apple-focus-reference-runtime-v5/frozen-inputs.tar.gz") as frozen:
        original_raw = frozen.extractfile("verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/products.tar.gz").read()
        original_manifest = frozen.extractfile("verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/product-manifest.json").read()
    assert sha(original_raw) == products["originalQualificationArchiveSHA256"]
    assert sha(original_manifest) == products["originalQualificationManifestSHA256"]
    originals = payload(original_raw)
    assert rows(originals) == json.loads(original_manifest)["products"]
    assert app == {n: v for n, v in originals.items() if n.startswith("MixerToggleDiagnostics.app/")}
    assert products["runnerProductsFresh"] and products["runnerProductFiles"] == 42
    assert all(n.startswith(("MixerToggleDiagnostics.app/", "runner-products/")) for n in product_values)
    commands = load(O / "commands.json")
    assert [c["name"] for c in commands] == ["xcode-version", "swift-version", "sdk-version", "runner-build"]
    for c in commands:
        assert c["exitCode"] == 0 and c["stdoutEOF"] and c["stderrEOF"] and c["processGroupAbsent"]
        assert not c["timedOut"] and not c["signalsSent"]
        for stream in ["stdout", "stderr"]:
            assert sha((O / (c["name"] + "." + stream)).read_bytes()) == c[stream + "SHA256"]
    old = load(R / "verification/apple-settings-instrumented-native-build/attempt-1/commands.json")[-1]
    current = commands[-1]
    old_scratch = str(R / "verification/apple-settings-instrumented-native-build/attempt-1/owned-build")
    current_scratch = str(O / "owned-build")
    assert [s.replace(old_scratch, "<OWNED>") for s in old["argv"]] == [s.replace(current_scratch, "<OWNED>") for s in current["argv"]]
    assert current["argv"][1] == "build-for-testing"
    assert current["argv"][current["argv"].index("-destination") + 1] == "generic/platform=iOS Simulator"
    tools = load(O / "tools.json")
    compiler = "/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift-frontend"
    assert tools["bindings"][compiler]["sha256"] == typecheck["compilerSHA256"]
    comparison = load(O / "warning-comparison.json")
    observed_warnings = warning_messages((O / "runner-build.stdout").read_bytes()) + warning_messages((O / "runner-build.stderr").read_bytes())
    assert observed_warnings == comparison["newWarnings"] and len(observed_warnings) == 15
    assert comparison["compilerAndMetadataWarnings"] == 7 and comparison["signedAppleFrameworkStrippingWarnings"] == 8
    for n, baseline in comparison["baselines"].items():
        raw = (R / n).read_bytes()
        assert sha(raw) == baseline["sha256"] and warning_messages(raw) == baseline["warnings"]
        assert collections.Counter(observed_warnings) == collections.Counter(baseline["warnings"]) and baseline["sameMessageMultiset"]
    driver = load(B / "driver-command.json")
    assert driver["exitCode"] == 0 and driver["processGroupAbsent"] and driver["stdoutEOF"] and driver["stderrEOF"]
    assert not driver["timedOut"] and not driver["signalsSent"] and not driver["survivingPIDs"]
    assert sha((B / "driver.stdout").read_bytes()) == driver["stdoutSHA256"]
    assert sha((B / "driver.stderr").read_bytes()) == driver["stderrSHA256"]
    cleanup = load(O / "cleanup.json")
    assert cleanup["ownedScratchRemoved"] and cleanup["holdersAbsent"] and cleanup["processGroupsAbsent"]
    assert cleanup["nativeInstancesTouched"] == 0 and not cleanup["otherProjectsTouched"]
    holder = load(O / "holder-check.json")
    assert holder["exitCode"] == 1 and not (O / "holders.stdout").read_bytes() and not (O / "holders.stderr").read_bytes()
    receipt = load(O / "receipt.json")
    assert receipt["passed"] and receipt["buildExitCode"] == 0 and receipt["sourceFiles"] == 40 and receipt["products"] == 55
    assert receipt["sourceTreeSHA256"] == source["sourceTreeSHA256"] and receipt["productTreeSHA256"] == products["productTreeSHA256"]
    assert receipt["buildScript"] == binding(B / "build.py")
    assert receipt["allWarningMessagesMatchOriginalAndPrior"] and receipt["allCommandsExitZeroEOFAndGroupsAbsent"]
    assert not receipt["nativeExecuted"] and not receipt["nativeExecutionSelected"] and not receipt["gaAccepted"] and not receipt["importerRebound"]
    return dict(passed=True, handoffSHA256=seal, sealedMembers=len(handoff["members"]), sourceFiles=40, products=55, originalApplicationFilesUnchanged=13, runnerProductFilesFresh=42, warningLines=15, warningMessagesMatchBothBaselines=True, producerMembers=176, reviewMembers=163, priorBuildMembers=22, ownedScratchAbsent=True, nativeExecuted=False, nativeExecutionSelected=False, importerRebound=False, gaAccepted=False)


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
