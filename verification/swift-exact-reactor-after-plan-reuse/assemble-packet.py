#!/usr/bin/env python3
"""Assemble only; never launch compiler, test executable or full target."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'verification/swift-exact-reactor-after-grouped-index'
CLOSURE = '16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
OLD_CLOSURE = '3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f'
old = (OLD / 'diagnostic.py').read_text()
new = old.replace('One bounded after-grouped-index exact Swift reactor diagnostic;',
                  'One bounded after-plan-reuse exact Swift reactor diagnostic;')
new = new.replace('HISTORY = ROOT / "verification/swift-exact-reactor-after-resident-index"',
                  'HISTORY = ROOT / "verification/swift-exact-reactor-after-grouped-index"')
new = new.replace('ACCEPTED = ROOT / "verification/swift-resident-index-grouped-reservation-root-integration"',
                  'ACCEPTED = ROOT / "verification/swift-decode-plan-root-integration"')
new = new.replace('MANIFEST = ACCEPTED / "integrated-manifest.json"',
                  'MANIFEST = ACCEPTED / "live-source-manifest.json"')
new = new.replace('CLOSURE = "' + OLD_CLOSURE + '"', 'CLOSURE = "' + CLOSURE + '"')
new = new.replace('HISTORICAL_CLOSURE = "02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d"',
                  'HISTORICAL_CLOSURE = "' + OLD_CLOSURE + '"')
new = new.replace('exact real Swift reactor after accepted private grouped index reservation',
                  'exact real Swift reactor after accepted private decode plan reuse')
start = new.index('def prepare():')
end = new.index('\n\ndef observe_group(', start)
prepare = '''def prepare():
    assert not (HERE / "binding.json").exists()
    assert not SCRATCH.exists() and not BASELINE.exists()
    assert sha(HERE / "harness.rs") == HARNESS_HASH == sha(HISTORY / "harness.rs")
    baseline = read(MANIFEST)
    assert len(baseline) == 132 and closure(baseline) == CLOSURE
    assert source_manifest(ROOT / "vm") == baseline
    assert sha(ACCEPTED / "acceptance.json") == "41ddd181ddd4af8940877e1b66379ffb7875c36af255483907304f68853dcef9"
    accepted = read(ACCEPTED / "acceptance.json")
    integration = read(ACCEPTED / "receipt.json")
    assert accepted["integrationAccepted"] and accepted["reviewedProductionUnchanged"]
    assert accepted["sourceClosure"] == integration["sourceClosure"] == CLOSURE
    assert accepted["receiptSHA256"] == sha(ACCEPTED / "receipt.json")
    assert accepted["liveTestsPassed"] == integration["namedPassed"] == 340
    assert accepted["liveTestsFailed"] == integration["namedFailed"] == 0
    assert accepted["liveTestsIgnored"] == integration["namedIgnored"] == 0
    assert integration["sourceUnchangedDuringTests"] and integration["testPassed"]
    assert integration["cleanup"]["scratchAbsent"] and integration["cleanup"]["ownedGroupsAbsent"]
    assert integration["cleanup"]["holdersEmpty"] and integration["cleanup"]["deviceInodeStable"]
    assert accepted["fullTargetExecuted"] is False and integration["fullReactorSelected"] is False
    assert accepted["nativeAccepted"] is False and accepted["gaAccepted"] is False
    selected_integration = read(ACCEPTED / "selection.json")
    assert selected_integration["originalSourceClosure"] == HISTORICAL_CLOSURE
    regression = selected_integration["verifiedBeforeMutation"]
    assert regression["exitCode"] == 0 and regression["finalNamedPasses"] == 2314
    assert regression["ignoredPerContext"] == 9 and regression["verifiedFiles"] == 560
    assert regression["externalBindings"] == 5 and regression["scratchAbsent"]
    assert selected_integration["regressionSealSHA256"] == accepted["regressionSealSHA256"]
    prior_manifest = read(HISTORY / "baseline-manifest.json")
    assert closure(prior_manifest) == HISTORICAL_CLOSURE
    changed = [name for name in baseline if baseline[name] != prior_manifest[name]]
    assert changed == selected_integration["changedPaths"] == [
        "src/experimental_swift_reactor/cache.rs",
        "src/experimental_swift_reactor/cache_tests.rs",
        "src/experimental_swift_reactor/execution_tests.rs",
        "src/experimental_swift_reactor/lifecycle_tests.rs"]
    assert sha(HISTORY / "prepared-seal.json") == "73c63e969ca2087b7e798e065b4adf1200d54f186aa5ffeb5dcc5971f066946b"
    assert sha(HISTORY / "result-seal.json") == "91c71f2c6b6520e141b9226f7675a4578d0d37865aa1dfcfafc9e4dad31acb8c"
    previous = read(HISTORY / "target-once-classification.json")
    assert previous["initializeCompleted"] and previous["corpus1Attempted"]
    assert not previous["corpus1Completed"] and not previous["corpus2Attempted"]
    failure = previous["firstTypedFailure"]
    assert (failure["resource"], failure["attempted"], failure["limit"], failure["function"], failure["offset"]) == (
        "CacheWork", 64000001, 64000000, 3416, 1077688)
    assert failure["at_failure"]["instructions"] == 15753076
    assert previous["finalCleanupReservationsAndLiveEmpty"] and previous["finalCleanupInvariant"] is None
    references = {}
    def retain(path, expected=None):
        path = Path(path)
        assert not any(part in str(path) for part in ("hosted-catalog-inspector", "hosted-authority-driver", "outbound-worker-transport-v2"))
        info = identity(path)
        if expected is not None:
            assert info["sha256"] == expected, str(path)
        references[str(path)] = info
    # Exact sealed prior result is data only; do not import or execute historical code.
    historical_seal = read(HISTORY / "result-seal.json")
    for name, expected in historical_seal["files"].items():
        retain(HISTORY / name, expected)
    for name, expected in historical_seal["externalFiles"].items():
        retain(ROOT / name, expected)
    for info in read(HISTORY / "binding.json")["inputs"]:
        retain(info["path"], info["sha256"])
    for path in (HISTORY / "prepared-seal.json", HISTORY / "result-seal.json", HISTORY / "root-selection.json",
                 MANIFEST, ACCEPTED / "selection.json", ACCEPTED / "receipt.json", ACCEPTED / "acceptance.json",
                 ACCEPTED / "commands.json", ACCEPTED / "format-derivative.json", ACCEPTED / "format-only.patch",
                 ROOT / "verification/swift-decode-plan-full-regression/seal.json"):
        retain(path)
    assert sha(ROOT / "verification/swift-decode-plan-full-regression/seal.json") == accepted["regressionSealSHA256"]
    contract_snapshots = []
    for name in ("AGENTS.md", "PLAN.md", "STATUS.md", "mixer-product-plan.md", "docs/swift-decode-plan-integration.md"):
        source = ROOT / name
        destination = HERE / "input-documents" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        assert sha(source) == sha(destination)
        retain(destination)
        contract_snapshots.append({"originalPath": str(source), "snapshot": str(destination.relative_to(HERE)), "sha256": sha(destination)})
    evidence = QUALIFIED / "evidence/2026-10-23-qualified"
    prior = read(evidence / "receipt.json")
    assert prior["fullSwiftSDK"] is True and prior["embeddedSwift"] is False
    assert prior["expectedObservation"] == EXPECTED and prior["native"]["observation"] == EXPECTED
    assert prior["candidateArtifactsBeforeOracle"]["reactor"]["sha256"] == REACTOR_HASH
    for name, expected in prior["sourceManifest"].items():
        retain(QUALIFIED / "local/2026-10-23-qualified/diagnostic-sources" / name, expected)
    for info in prior["inputs"].values():
        retain(info["path"], info["sha256"])
    for info in prior["native"].values():
        if isinstance(info, dict) and "path" in info:
            retain(info["path"], info["sha256"])
    for name in ("receipt.json", "native-command-run.stdout", "descriptors.json", "structure.json"):
        retain(evidence / name)
    native = strict_json((evidence / "native-command-run.stdout").read_text())
    assert set(native) == set(EXPECTED) and len(native) == 11
    assert all(type(native[k]) is type(EXPECTED[k]) and native[k] == EXPECTED[k] for k in EXPECTED)
    assert REACTOR.stat().st_size == 53_777_114 and sha(REACTOR) == REACTOR_HASH
    SCRATCH.mkdir(mode=0o700)
    (SCRATCH / "tmp").mkdir(mode=0o700)
    for name, expected in baseline.items():
        src = ROOT / "vm" / name
        assert sha(src) == expected
        for destination in (BASELINE / name, SOURCE / name):
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, destination)
            assert sha(destination) == expected
    test = SOURCE / "src/experimental_swift_reactor/lifecycle_tests.rs"
    with test.open("ab") as stream:
        stream.write(APPEND.encode())
    save("baseline-manifest.json", baseline)
    save("binding.json", {"schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "baselineClosure": CLOSURE, "historicalClosure": HISTORICAL_CLOSURE,
        "sourceRevisionContext": "9102ad3ee1247187c01ea5f55c42caaac882961b",
        "sourceRevisionMeaning": "root-supplied revision context plus accepted uncommitted four-file integration; exact content closure authoritative; no clean-commit assertion or Git query",
        "inputs": list(references.values()), "contractSnapshots": contract_snapshots,
        "target": identity(REACTOR), "expectedObservation": EXPECTED,
        "historicalFailurePacket": identity(HISTORY / "result-seal.json"),
        "acceptedPrivateDecodePlanReuse": identity(ACCEPTED / "acceptance.json"),
        "historicalInputDisposition": "hash references only; no old driver, compiler, native binary or Node execution",
        "selectedPhases": ["complete validation", "adoption", "construct original owner", "Initialize35", "Corpus62", "Corpus62", "consuming cleanup"],
        "targetExecutionSelectedByRoot": False, "productionBaselineModifiedByDiagnostic": False,
        "hostDiagnosticOnly": True, "productionCallerStackOrAccountingCredit": False,
        "historicalNativeAndNodeOnlyDataReferences": True, "nativePhysicalOrEmulatorRun": False,
        "compilerTools": tools()})
    save("copied-build-manifest.json", assert_baseline())
    print(json.dumps({"prepared": True, "files": 132, "closure": CLOSURE, "targetExecuted": False}))
'''
new = new[:start] + prepare + new[end:]
old_functions = {n.name:n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef)}
new_functions = {n.name:n for n in ast.parse(new).body if isinstance(n,ast.FunctionDef)}
assert set(old_functions) == set(new_functions)
unchanged=[]
for name in old_functions:
    if name == 'prepare': continue
    a=ast.get_source_segment(old,old_functions[name])
    b=ast.get_source_segment(new,new_functions[name])
    if name == 'execute':
        b=b.replace('exact real Swift reactor after accepted private decode plan reuse',
                    'exact real Swift reactor after accepted private grouped index reservation')
    assert a == b, name
    unchanged.append(name)
(HERE/'diagnostic.py').write_text(new)
for name in ('harness.rs','test_driver.py','run-preparation-step.py'):
    shutil.copyfile(OLD/name,HERE/name)
(HERE/'verify.py').write_text((OLD/'verify.py').read_text().replace(OLD_CLOSURE,CLOSURE))
(HERE/'driver-changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
    fromfile='swift-exact-reactor-after-grouped-index/diagnostic.py', tofile='swift-exact-reactor-after-plan-reuse/diagnostic.py')))
(HERE/'static-assembly-check.json').write_text(json.dumps({'schema':1,'allFunctionsPresent':True,
    'unchangedDriverFunctions':unchanged,'executeOnlyChange':'human-readable source-integration label',
    'fullTargetExecuted':False,'historicalDriverExecuted':False},indent=2,sort_keys=True)+'\n')
print(json.dumps({'assembled':True,'unchangedFunctions':len(unchanged),'targetExecuted':False}))
