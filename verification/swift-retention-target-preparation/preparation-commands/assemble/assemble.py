#!/usr/bin/env python3
"""Prepare isolated sources/driver only; no target execution or old packet mutation."""
from pathlib import Path
import datetime
import difflib
import gzip
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tarfile
from packetlib import (HERE as H, ROOT, CANDIDATE, CANDIDATE_SEAL, CANDIDATE_CLOSURE,
                       LIVE_BASELINE_CLOSURE, HARNESS_HASH, candidate_payloads,
                       closure, read, sha, verify_candidate, write_source)

ORIGINAL = ROOT / 'verification/swift-exact-reactor-after-plan-reuse'
assert not (H / 'binding.json').exists() and not (H / 'owned-scratch').exists()
assert H == ROOT / 'verification/swift-retention-target-preparation'
verify_candidate()
assert sha(ORIGINAL / 'harness.rs') == HARNESS_HASH
for name in ('harness.rs', 'diagnostic.py', 'test_driver.py'):
    destination = H / 'historical-code' / name
    destination.parent.mkdir(exist_ok=True)
    shutil.copyfile(ORIGINAL / name, destination)
shutil.copyfile(ORIGINAL / 'harness.rs', H / 'harness.rs')
shutil.copyfile(ORIGINAL / 'test_driver.py', H / 'test_driver.py')
original = (ORIGINAL / 'diagnostic.py').read_text()
driver = original.replace('One bounded after-plan-reuse exact Swift reactor diagnostic; no live VM writes.',
                          'One bounded isolated retention-candidate exact Swift diagnostic; fresh root selection required.')
driver = driver.replace('import time\n', 'import time\nfrom packetlib import (candidate_payloads, verify_candidate, verify_prepared_seal, accepted_review,\n                       CANDIDATE_CLOSURE, LIVE_BASELINE_CLOSURE, CANDIDATE_SEAL)\n')
start = driver.index('BASELINE = HERE / "baseline"\n')
end = driver.index('REACTOR = QUALIFIED', start)
driver = driver[:start] + '''QUALIFIED = ROOT / "compiler/experiments/fieldlog-reactor"
CLOSURE = CANDIDATE_CLOSURE
HARNESS_HASH = "d72da7bc7aaf4e31b7093fde497f357226d3a4dd954eb577909209102a0bfb00"
''' + driver[end:]
driver = driver.replace('baseline production bytes are unchanged.', 'isolated candidate production bytes are unchanged.')
driver = driver.replace('CARGO_NET_OFFLINE="true", CARGO_TARGET_DIR=str(TARGET),',
                        'CARGO_NET_OFFLINE="true", CARGO_BUILD_JOBS="2", CARGO_TARGET_DIR=str(TARGET),')
start = driver.index('def assert_baseline():\n')
end = driver.index('\n\ndef assert_inputs():', start)
driver = driver[:start] + '''def reconstructed_source():
    payloads = candidate_payloads()
    test = "src/experimental_swift_reactor/lifecycle_tests.rs"
    payloads[test] += APPEND.encode()
    return payloads


def assert_baseline():
    # This is the selected isolated candidate closure, never the live VM closure.
    bound = read(HERE / "candidate-manifest.json")
    assert len(bound) == 132 and closure(bound) == CANDIDATE_CLOSURE
    expected = read(HERE / "copied-build-manifest.json")
    reconstructed = {name: hashlib.sha256(data).hexdigest()
                     for name, data in reconstructed_source().items()}
    assert reconstructed == expected
    modified = source_manifest(SOURCE)
    assert modified == expected, "isolated source drift"
    assert [name for name in bound if bound[name] != modified[name]] == [
        "src/experimental_swift_reactor/lifecycle_tests.rs"]
    return modified
''' + driver[end:]
start = driver.index('def prepare():\n')
end = driver.index('def observe_group(', start)
driver = driver[:start] + driver[end:]
# The exact original supervisor, parser, tool inventory and cleanup remain literal.
target_guard = '''        seal = verify_prepared_seal()
        assert selection["preparedSealSHA256"] == sha(HERE / "prepared-seal.json")
        assert selection["candidateSealSHA256"] == CANDIDATE_SEAL
        assert selection["candidateManifestSHA256"] == CANDIDATE_CLOSURE
        assert selection["liveBaselineClosureSHA256"] == LIVE_BASELINE_CLOSURE
        assert selection["candidateLiveIntegrated"] is False
        assert selection["rootSelectionAuthority"] == "fresh-root-selection-after-accepted-independent-review"
        assert selection["compilerTools"] == tools() == read(HERE / "binding.json")["compilerTools"]
        assert selection["sourceManifestSHA256"] == sha(HERE / "copied-build-manifest.json")
        accepted_review(selection)
        selected_at = datetime.datetime.fromisoformat(selection["selectedUTC"])
        prepared_at = datetime.datetime.fromisoformat(seal["sealedUTC"])
        review_seal = read(selection["reviewSealPath"])
        reviewed_at = datetime.datetime.fromisoformat(review_seal["sealedUTC"])
        assert selected_at.tzinfo is not None and selected_at > max(prepared_at, reviewed_at)
'''
needle = '        selection = read(HERE / "root-selection.json")\n'
assert driver.count(needle) == 1
driver = driver.replace(needle, needle + target_guard)
driver = driver.replace('exact real Swift reactor after accepted private decode plan reuse',
                        'exact real Swift reactor with isolated retention candidate; no live integration or attribution')
driver = driver.replace('byte-identical selected harness and accepted baseline',
                        'byte-identical original selected harness; isolated retention candidate')
driver = driver.replace('"baseline-manifest.json", "copied-build-manifest.json"',
                        '"candidate-manifest.json", "live-baseline-manifest.json", "copied-build-manifest.json"')
driver = driver.replace('"scope": "host diagnostic only;', '"candidateManifestSHA256": CANDIDATE_CLOSURE, "liveBaselineClosureSHA256": LIVE_BASELINE_CLOSURE,\n        "candidateLiveIntegrated": False, "candidateSealSHA256": CANDIDATE_SEAL,\n        "scope": "host diagnostic only;')
driver = driver.replace('choices=("prepare", "build", "control", "host-controls", "propose", "target", "cleanup")',
                        'choices=("build", "control", "host-controls", "propose", "target", "cleanup")')
driver = driver.replace('return {"prepare": prepare, "build": build,', 'return {"build": build,')
(H / 'diagnostic.py').write_text(driver)
(H / 'driver-changes.diff').write_text(''.join(difflib.unified_diff(
    original.splitlines(True), driver.splitlines(True),
    fromfile='historical-code/diagnostic.py', tofile='diagnostic.py')))
# Assert exact function bytes for the inherited authority and host safety mechanisms.
import ast
old_ast, new_ast = ast.parse(original), ast.parse(driver)
def function_text(text, tree, name):
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ''.join(text.splitlines(True)[node.lineno-1:node.end_lineno])
unchanged = ['sha','save','read','identity','tools','source_manifest','closure','assert_inputs',
             'observe_group','record_command','build','strict_json','events','cleanup','host_controls']
for name in unchanged:
    assert function_text(original, old_ast, name) == function_text(driver, new_ast, name), name
save = lambda name, value: (H / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
save('source-audit.json', {'schema':1, 'originalHarnessSHA256':HARNESS_HASH,
    'harnessByteIdentical':sha(H/'harness.rs') == sha(ORIGINAL/'harness.rs'),
    'testDriverByteIdentical':sha(H/'test_driver.py') == sha(ORIGINAL/'test_driver.py'),
    'literalUnchangedFunctions':unchanged, 'prepareCLIRemoved':True,
    'inheritedHistoricalCodeExecuted':False, 'sourcePathsWritten':['owned-scratch/vm'],
    'liveSourceReadOrWritten':False, 'rootSuppliedRevision':'b375e55ded9e3e10c327891ab681beff2a471e26'})
shutil.copyfile(CANDIDATE / 'candidate-manifest.json', H / 'candidate-manifest.json')
shutil.copyfile(CANDIDATE / 'baseline-manifest.json', H / 'live-baseline-manifest.json')
payloads = candidate_payloads()
append = '\n// Isolated diagnostic only; isolated candidate production bytes are unchanged.\ninclude!(' + json.dumps(str(H / 'harness.rs')) + ');\n'
payloads['src/experimental_swift_reactor/lifecycle_tests.rs'] += append.encode()
manifest = {name:hashlib.sha256(data).hexdigest() for name,data in payloads.items()}
save('copied-build-manifest.json', manifest)
scratch = H / 'owned-scratch'
scratch.mkdir(mode=0o700)
(scratch / 'tmp').mkdir(mode=0o700)
write_source(payloads, scratch / 'vm')
with (H / 'prepared-source.tar.gz').open('xb') as raw:
    with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w', format=tarfile.USTAR_FORMAT) as archive:
            for name,data in sorted(payloads.items()):
                entry=tarfile.TarInfo(name);entry.size=len(data);entry.mode=0o600;entry.mtime=0
                archive.addfile(entry, io.BytesIO(data))
spec = importlib.util.spec_from_file_location('retention_preparation_driver', H / 'diagnostic.py')
d = importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
assert d.APPEND == append and d.assert_baseline() == manifest
references = {}
def retain(path):
    info = d.identity(path);references[info['path']] = info
seal = verify_candidate()
for name in seal['members']:
    retain(CANDIDATE / name)
for name in seal['externalMembers']:
    retain(ROOT / name)
retain(CANDIDATE / 'seal.json')
for name in ('diagnostic.py', 'test_driver.py', 'harness.rs'):
    retain(ORIGINAL / name)
evidence = ROOT / 'compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified'
native = d.strict_json((evidence / 'native-command-run.stdout').read_text())
assert set(native) == set(d.EXPECTED) and len(native) == 11
assert all(type(native[k]) is type(d.EXPECTED[k]) and native[k] == d.EXPECTED[k] for k in native)
for name in ('receipt.json','native-command-run.stdout','descriptors.json','structure.json'):
    retain(evidence/name)
assert d.REACTOR.stat().st_size == 53_777_114 and sha(d.REACTOR) == d.REACTOR_HASH
for name in ('AGENTS.md', 'PLAN.md', 'STATUS.md', 'mixer-product-plan.md'):
    destination = H / 'context' / name;destination.parent.mkdir(exist_ok=True)
    shutil.copyfile(ROOT/name, destination)
save('binding.json', {'schema':1, 'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevisionContext':'b375e55ded9e3e10c327891ab681beff2a471e26',
    'sourceRevisionMeaning':'root supplied context; exact isolated archive/manifest authoritative; no Git query',
    'baselineClosure':CANDIDATE_CLOSURE, 'baselineClosureMeaning':'selected isolated candidate, never live-integrated',
    'candidateManifestSHA256':CANDIDATE_CLOSURE, 'liveBaselineClosureSHA256':LIVE_BASELINE_CLOSURE,
    'candidateSealSHA256':CANDIDATE_SEAL, 'candidateLiveIntegrated':False,
    'copiedBuildManifestSHA256':closure(manifest), 'inputs':list(references.values()),
    'target':d.identity(d.REACTOR), 'expectedObservation':d.EXPECTED, 'compilerTools':d.tools(),
    'targetExecutionSelectedByRoot':False, 'fullTargetAttempts':0, 'liveVMReadOrModified':False,
    'archiveBounds':{'members':132,'totalBytes':24*1024*1024,'memberBytes':16*1024*1024,'compressedBytes':2*1024*1024},
    'finiteTradeoffs':read(CANDIDATE/'handoff.json')['materialTradeoffs'],
    'nativeOracleDisposition':'historical data only; no native oracle execution',
    'selectedPhases':['complete validation','adoption','construct original owner','Initialize35','Corpus62','Corpus62','consuming cleanup']})
d.assert_inputs()
print(json.dumps({'isolatedPrepared':True,'sourceFiles':len(manifest),'candidateClosure':CANDIDATE_CLOSURE,
    'copiedBuildClosure':closure(manifest),'liveBaselineClosure':LIVE_BASELINE_CLOSURE,'targetExecuted':False}))
