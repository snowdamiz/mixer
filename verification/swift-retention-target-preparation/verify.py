#!/usr/bin/env python3
"""Read-only prepared-packet verification; no subprocess, build, source restore or guest execution."""
from pathlib import Path
import ast
import gzip
import hashlib
import json
from packetlib import (HERE as H, ROOT, CANDIDATE, CANDIDATE_SEAL, CANDIDATE_CLOSURE,
                       LIVE_BASELINE_CLOSURE, HARNESS_HASH, archive_payloads,
                       candidate_payloads, closure, read, sha, verify_candidate,
                       verify_prepared_seal)


def source_manifest(directory):
    paths=[directory/'Cargo.toml', directory/'Cargo.lock']
    paths += [p for top in ('include','src','tests') for p in (directory/top).rglob('*') if p.is_file()]
    return {str(p.relative_to(directory)):sha(p) for p in sorted(paths)}


def strict(text):
    def pairs(items):
        result={}
        for key,value in items:
            assert key not in result, key
            result[key]=value
        return result
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def raw_events(path):
    result=[]
    for line in path.read_text().splitlines():
        at=line.find('MIXER_EXACT ')
        if at >= 0:
            result.append(strict(line[at+len('MIXER_EXACT '):]))
    return result


def function(text,name):
    node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name)
    return ''.join(text.splitlines(True)[node.lineno-1:node.end_lineno])


def main():
    assert not (H/'target-attempt-started.json').exists(), 'preparation verifier only'
    assert not (H/'commands/target-once').exists()
    seal=verify_prepared_seal()
    verify_candidate()
    candidate=read(H/'candidate-manifest.json')
    baseline=read(H/'live-baseline-manifest.json')
    assert len(candidate)==len(baseline)==132
    assert closure(candidate)==CANDIDATE_CLOSURE and closure(baseline)==LIVE_BASELINE_CLOSURE
    assert sha(H/'harness.rs')==sha(H/'historical-code/harness.rs')==HARNESS_HASH
    assert sha(H/'test_driver.py')==sha(H/'historical-code/test_driver.py')
    old=(H/'historical-code/diagnostic.py').read_text()
    current=(H/'diagnostic.py').read_text()
    audit=read(H/'source-audit.json')
    for name in audit['literalUnchangedFunctions']:
        assert function(old,name)==function(current,name), name
    main_text=function(current,'main')
    assert '"prepare"' not in main_text and 'prepare' not in {n.name for n in ast.parse(current).body if isinstance(n,ast.FunctionDef)}
    expected=candidate_payloads()
    append='\n// Isolated diagnostic only; isolated candidate production bytes are unchanged.\ninclude!('+json.dumps(str(H/'harness.rs'))+');\n'
    expected['src/experimental_swift_reactor/lifecycle_tests.rs']+=append.encode()
    built=read(H/'copied-build-manifest.json')
    assert {name:hashlib.sha256(data).hexdigest() for name,data in expected.items()}==built
    restored=archive_payloads(H/'prepared-source.tar.gz',built)
    assert restored==expected
    assert [name for name in candidate if candidate[name]!=built[name]]==['src/experimental_swift_reactor/lifecycle_tests.rs']
    binary=read(H/'binary.json')
    retained=binary['retained']
    assert binary['buildManifest']==built and binary['harnessSHA256']==HARNESS_HASH
    assert 0 < retained['bytes'] <= 16*1024*1024
    with gzip.open(H/'bin/exact-tests.gz','rb') as stream:
        data=stream.read(retained['bytes']+1)
    assert len(data)==retained['bytes'] and hashlib.sha256(data).hexdigest()==retained['sha256']
    if (H/'bin/exact-tests').exists():
        assert sha(H/'bin/exact-tests')==retained['sha256']
    if (H/'owned-scratch').exists():
        assert not (H/'owned-scratch').is_symlink()
        assert source_manifest(H/'owned-scratch/vm')==built
        assert not (H/'owned-scratch/target').exists()
        assert not (H/'owned-scratch/fieldlog-reactor.wasm').exists()
    binding=read(H/'binding.json')
    assert binding['candidateManifestSHA256']==CANDIDATE_CLOSURE
    assert binding['liveBaselineClosureSHA256']==LIVE_BASELINE_CLOSURE
    assert binding['candidateSealSHA256']==CANDIDATE_SEAL and binding['candidateLiveIntegrated'] is False
    assert binding['fullTargetAttempts']==0 and binding['liveVMReadOrModified'] is False
    assert binding['copiedBuildManifestSHA256']==closure(built)
    for info in binding['inputs']:
        assert sha(info['path'])==info['sha256'], info['path']
    target=binding['target']
    assert Path(target['path']).stat().st_size==target['bytes']==53_777_114
    assert sha(target['path'])==target['sha256']=='24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994'
    tools=binding['compilerTools']
    assert sha(tools['python']['path'])==tools['python']['sha256']
    for name in ('cargo','rustc','rustup'):
        for kind in ('proxy','actual'):
            info=tools[name][kind]
            assert sha(info['path'])==info['sha256']
    for name,digest in tools['sysroot']['files'].items():
        assert sha(Path(tools['sysroot']['path'])/name)==digest, name
    proposal=read(H/'prepared-selection.json')
    assert proposal['status']=='prepared-awaiting-root-exact-selection'
    assert proposal['candidateManifestSHA256']==CANDIDATE_CLOSURE
    assert proposal['liveBaselineClosureSHA256']==LIVE_BASELINE_CLOSURE
    assert proposal['candidateLiveIntegrated'] is False and proposal['candidateSealSHA256']==CANDIDATE_SEAL
    assert proposal['targetAttempted'] is False and proposal['maxTargetAttempts']==1
    assert proposal['binarySHA256']==retained['sha256'] and proposal['harnessSHA256']==HARNESS_HASH
    assert proposal['driverSHA256']==sha(H/'diagnostic.py') and proposal['inputBindingSHA256']==sha(H/'binding.json')
    for name,digest in proposal['boundEvidence'].items():
        assert sha(H/name)==digest, name
    commands=[]
    for path in sorted((H/'commands').glob('*/receipt.json')):
        command=read(path)
        assert command['passed'] and command['exitCode']==0 and not command['timedOut']
        assert command['sourceClosure']==closure(built) and command['baselineClosure']==CANDIDATE_CLOSURE
        assert command['processGroupEmpty'] and command['finalGroupObservation']['state']=='absent'
        assert command['rawStreamEOFConfirmed'] and command['signalSent']==[]
        for field in ('sourceUnchanged','toolsUnchanged','allBoundInputsUnchanged','harnessUnchanged','driverUnchanged','argvFilesUnchanged'):
            assert command[field], (path,field)
        for stream in ('stdout','stderr'):
            assert sha(path.parent/stream)==command[stream]['sha256']
        assert sha(path.parent/'harness.rs')==command['harnessSHA256']==HARNESS_HASH
        assert sha(path.parent/'diagnostic.py')==command['driverSHA256']==sha(H/'diagnostic.py')
        assert read(path.parent/'source-manifest.json')==built
        commands.append(path.parent.name)
    assert commands==['build-001','control-001','control-002','driver-observation-controls','list-001']
    for name in ('control-001','control-002'):
        observed=read(H/(name+'-events.json'))
        assert observed==raw_events(H/'commands'/name/'stdout')
        result=read(H/(name+'-result.json'))
        assert result['commandPassed'] and result['diagnosticCompleted'] and result['ownedCleanupEmpty']
        assert result['targetAttempted'] is False and result['firstFailure'] is None
        by_name={event['event']:event['payload'] for event in observed}
        assert by_name['cleanup_reservations_and_live_empty'] is True
        assert by_name['diagnostic_execution_complete'] is True
        assert result['phasesBegun']==['validation','initialize','corpus_1','corpus_2']
    stderr=(H/'commands/driver-observation-controls/stderr').read_text()
    assert 'Ran 10 tests' in stderr and stderr.rstrip().endswith('OK')
    wrappers=[]
    for path in sorted((H/'preparation-commands').glob('*/receipt.json')):
        command=read(path)
        assert command['finalGroupState']=='absent' and command['signals']==[]
        assert not command['targetExecutionAllowed'] and not command['timedOut']
        assert command['scriptUnchanged']
        assert sha(path.parent/'stdout')==command['stdoutSHA256']
        assert sha(path.parent/'stderr')==command['stderrSHA256']
        assert command['passed']==(path.parent.name!='assemble')
        wrappers.append(path.parent.name)
    assert wrappers==['assemble','assemble-002','build','cleanup','control-001','control-002','host-controls','host-review-controls','propose']
    review_stderr=(H/'preparation-commands/host-review-controls/stderr').read_text()
    assert 'Ran 8 tests' in review_stderr and review_stderr.rstrip().endswith('OK')
    cleanup=read(H/'cleanup.json')
    assert cleanup['removed'] and cleanup['holderExitCode']==1
    assert cleanup['retainedExecutable']['uncompressed']['sha256']==retained['sha256']
    assert cleanup['retainedExecutable']['gzip']['sha256']==sha(H/'bin/exact-tests.gz')
    for name in ('scratch-holders.stdout','scratch-holders.stderr','binary-holders.stdout','binary-holders.stderr'):
        assert (H/name).read_bytes()==b''
    receipt=read(H/'receipt.json')
    assert receipt['fullTargetAttempts']==0 and receipt['candidateLiveIntegrated'] is False
    assert receipt['rootSelectionCreated'] is False and receipt['independentReviewRequiredBeforeSelection'] is True
    print(json.dumps({'preparedIntegrityVerified':True,'retainedMembers':len(seal['files']),
        'candidateFiles':132,'candidateManifestSHA256':CANDIDATE_CLOSURE,
        'liveBaselineClosureSHA256':LIVE_BASELINE_CLOSURE,'copiedBuildManifestSHA256':closure(built),
        'releaseNoRunBuildsPassed':1,'syntheticHarnessControlsPassed':2,
        'hostProcessControlsPassed':10,'hostReviewGuardTestsPassed':8,'fullTargetAttempts':0,
        'rootSelectionRequiredAfterAcceptedIndependentReview':True,'gaAccepted':False}))


if __name__=='__main__':
    main()
