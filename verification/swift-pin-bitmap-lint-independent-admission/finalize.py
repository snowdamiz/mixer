#!/usr/bin/env python3
"""Freeze lean source review and host proposal. Never invoke a host command."""
import offline
offline.install()
import ast, datetime, hashlib, json, sys
from pathlib import Path
import admit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def row(path):
    raw=path.read_bytes(); return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def save(name,value):
    (HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')


review=json.loads((HERE/'review-controls-result.json').read_text())
host=json.loads((HERE/'host-controls-result.json').read_text())
assert review['tests']==8 and host['tests']==27
for result in (review,host):
    assert result['failures']==result['errors']==result['skips']==0
    assert not result['liveApiAttempts']
assert not list(HERE.glob('pure-*'))
for path in HERE.glob('*.py'):ast.parse(path.read_text())
manifest,data=admit.inputs()
source=Path('$RUNNER_TEMP')/(admit.PROFILE+'-evidence')/'scratch'
paths={n:source/n for n in ('source','target','cargo','home','nodebin')}
tool=Path('$RUSTUP_HOME')/'toolchains'/admit.TOOLCHAIN/'bin'
plan=admit.command_plan(paths,tool,source/'rustfmt.toml',{'path':'$NODE_REALPATH'})
save('command-plan.json',{'schema':1,'selected':False,'profile':admit.PROFILE,'commands':plan,'activeSeconds':1800,'cleanupSeconds':60,'maxChildren':6,'perStreamBytes':8388608,'aggregateBytes':33554432,'pathExpansions':{'$RUNNER_TEMP':'Fresh hosted runner temporary directory, validated distinct from checkout','$RUSTUP_HOME':'$RUNNER_TEMP/swift-pin-bitmap-lint-regression-v1-toolchain','$NODE_REALPATH':'Sole existing Node resolution frozen before managed commands; no fallback or install'},'expectedDebugPassed':699,'expectedReleasePassed':699,'ignored':0})
basis={
    'AGENTS.md':row(ROOT/'AGENTS.md'),
    'mixer-product-plan.md':row(ROOT/'mixer-product-plan.md'),
    'verification/swift-pin-bitmap-lint-correction/seal.json':row(ROOT/'verification/swift-pin-bitmap-lint-correction/seal.json'),
    'verification/swift-pin-bitmap-lint-correction/manifest.json':row(ROOT/'verification/swift-pin-bitmap-lint-correction/manifest.json'),
    'verification/clock-format-actual-results/sanitized-result.json':row(ROOT/'verification/clock-format-actual-results/sanitized-result.json'),
    'verification/clock-format-actual-results/seal.json':row(ROOT/'verification/clock-format-actual-results/seal.json'),
    'verification/swift-pin-bitmap-format-lint-host-correction/admit.py':row(ROOT/'verification/swift-pin-bitmap-format-lint-host-correction/admit.py'),
    'verification/swift-pin-bitmap-format-lint-host-correction/bounded_commands.py':row(ROOT/'verification/swift-pin-bitmap-format-lint-host-correction/bounded_commands.py'),
}
save('source-basis.json',{'schema':1,'parentSuppliedHead':'6d57e05e58e6d614e58a0a4dc0fad661264fb46f','GitVerification':False,'files':basis,'baselineTreeSHA256':admit.BASELINE,'candidateTreeSHA256':admit.CANDIDATE,'sourceMembers':136,'overlays':15,'allRawActualBindingsVerifiedBy':'review_controls.py; actual-bindings.json remains in producer packet','rawCIArtifactsCopied':False,'sourcePolicy':'product-plan sections 20.3 and 24.4; active user pause and custody holds preserved'})
save('receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'decision':'Source accepted for bounded host verification only; proposal unselected','assignedRole':{'model':'gpt-6-astra','reasoningEffort':'xhigh','context':'fresh independent escalation; parent-assigned, no controlling-model change'},'parentSuppliedHead':'6d57e05e58e6d614e58a0a4dc0fad661264fb46f','candidateTreeSHA256':admit.CANDIDATE,'sourceControls':{'passed':8,'dataAssertions':review['dataAssertions']},'hostControls':{'passed':27,'mockedOnly':True},'commands':['python3 -B verification/swift-pin-bitmap-lint-independent-admission/review_controls.py','python3 -B verification/swift-pin-bitmap-lint-independent-admission/prepare_proposal.py','python3 -B verification/swift-pin-bitmap-lint-independent-admission/host_controls.py','python3 -B verification/swift-pin-bitmap-lint-independent-admission/finalize.py'],'pythonVersion':sys.version,'RustNodeSwiftElixirCompilerProductRuntimeRuns':0,'nativeUICaptureRuns':0,'GitGhDispatchActions':0,'canonicalFilesEdited':False,'workflowInstalled':False,'selected':False,'realNestedProcessSessionGroupSignalTimerWaitSocketCalls':0,'allSuccessfulGuardsHadZeroLiveAttempts':True,'preparationFailures':'preparation-history.json','cleanup':{'disposablePureScratchRemaining':0,'runtimeInstancesStarted':0,'heldProcessesProbed':False,'onlyOwnedPacketWritten':True},'FieldLogPreserved':{'run':40802230894,'pgid':2424,'pid':2621,'probedSignalledRetried':False},'pending':['root proposal selection','host compiler identity, formatting, strict lint and 699-test Debug/Release execution','independent actual artifact interpretation and canonical integration','native/physical/published-package FieldLog/GA evidence'],'publicSignedOTAFieldLogGAQualified':False})
# Generated fragments and the one-time cleanup utility are local preparation
# aids; the exact reused functions and failure record are already lean-bound.
for name in ('generic_source.py.fragment','cleanup_preparation.py'):
    path=HERE/name
    if path.exists():
        local=HERE/'local';local.mkdir(exist_ok=True)
        (local/name).write_bytes(path.read_bytes());path.unlink()
files={p.relative_to(HERE).as_posix():row(p) for p in HERE.rglob('*') if p.is_file() and 'local' not in p.relative_to(HERE).parts and p.name!='seal.json'}
assert not any('pure-' in n or '__pycache__' in n for n in files)
save('seal.json',{'schema':1,'scope':'Lean independent source review and unselected six-child hosted proposal; no runtime acceptance','files':dict(sorted(files.items())),'treeSHA256':admit.closure(files),'candidateTreeSHA256':admit.CANDIDATE,'rawLogsAndArtifactsLocalOnly':True})
print(json.dumps({'members':len(files),'sealSHA256':row(HERE/'seal.json')['sha256'],'treeSHA256':admit.closure(files),'sourceControls':8,'hostControls':27,'RustRuns':0,'selected':False}))
