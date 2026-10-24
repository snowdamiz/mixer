#!/usr/bin/env python3
"""Seal this lane's host-only proposed-contract packet, including nested receipts."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[1]
DOC = ROOT / 'docs/android-authored-toggle-input-contract.md'

def sha(data): return hashlib.sha256(data).hexdigest()
def entry(path):
    data=path.read_bytes()
    return {'bytes':len(data),'sha256':sha(data)}
def put(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

def main():
    assert sys.dont_write_bytecode, 'Use python3 -B'
    inputs=json.loads((OUT/'input-bindings.json').read_text())
    for name,expected in inputs.items():
        assert entry(OUT/expected['snapshot']) == {k:expected[k] for k in ('bytes','sha256')}, name
        assert entry(ROOT/name) == {k:expected[k] for k in ('bytes','sha256')}, 'Live input changed after snapshot: '+name
    original=json.loads((OUT/'inputs/verification/android-pointer-native-diagnosis/analysis-1/input-bindings.json').read_text())
    fixture_names=('verification/android-pointer-oracle-repair/CoordinatorJoinInstrumentation.java',
                   'verification/android-pointer-oracle-repair/CoordinatorJoinActivity.java')
    for name in fixture_names:
        assert entry(ROOT/name) == original[name], 'Immutable native fixture changed: '+name
    argv=[sys.executable,'-B',str(OUT/'test_contract.py')]
    result=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
    output=OUT/'commands/host-tests.log';output.write_bytes(result.stdout)
    assert result.returncode==0, result.stdout.decode()
    assert b'Ran 16 tests' in result.stdout and result.stdout.rstrip().endswith(b'OK')
    # In-memory syntax compilation creates no scratch directory or pyc.
    for filename in ('capture_inputs.py','contract_model.py','test_contract.py','finalize.py'):
        compile((OUT/filename).read_bytes(),str(OUT/filename),'exec')
    capture=json.loads((OUT/'capture-receipt.json').read_text())
    receipt={
        'schema':1,'status':'passed-host-proposed-contract-only',
        'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command':[sys.executable,'-B',str(pathlib.Path(__file__).resolve())],
        'pythonVersion':sys.version,'pythonExecutable':sys.executable,
        'pythonExecutableSHA256':sha(pathlib.Path(sys.executable).resolve().read_bytes()),
        'sourceInputClosureSHA256':capture['sourceInputClosureSHA256'],
        'sourceInputsVerified':len(inputs),'diagnosisFilesVerified':20,
        'diagnosisSealSHA256':capture['diagnosisSealSHA256'],
        'nativeFixtureFilesUnchanged':{name:entry(ROOT/name) for name in fixture_names},
        'hostTests':16,'syntaxFilesCompiledInMemory':4,
        'commands':[{'argv':argv,'cwd':str(ROOT),'exitCode':result.returncode,
                     'output':str(output.relative_to(OUT)),'outputSHA256':sha(result.stdout)}],
        'currentTreeIdentity':'Copied input source closure; no Git invoked',
        'limitations':[
            'Executable model covers proposed arithmetic/state semantics only, imports no production adapter and emulates no Android framework.',
            'No native build, emulator, device, UI, keyboard, accessibility, JNI or scroll acceptance.',
            'P01/P02 prior native pass and P03 prior failure remain unchanged; original20-action matrix remains unaccepted.',
            'Root has not selected production implementation or assigned product-file ownership.',
            'Physical phones remain disconnected/deferred; no discovery or reconnect request.',
        ],
        'rootImplementationSelected':False,'productionFilesChangedByLane':False,
        'nativeToolsInvoked':0,'gitCommands':0,'trackerFilesChanged':0,
        'scratch':{'created':False,'remaining':False,'reason':'In-memory compilation; all retained files are owned proof artifacts; -B prevents pycache'},
    }
    put(OUT/'receipt.json',receipt)
    message={'status':receipt['status'],'hostTests':16,'inputsVerified':len(inputs),'nativeAccepted':False,'scratchRemaining':False}
    (OUT/'commands/finalize.log').write_text(json.dumps(message)+'\n')
    files=[DOC]+[p for p in OUT.rglob('*') if p.is_file() and p.name!='packet-seal.json']
    assert not any(p.name=='__pycache__' for p in OUT.rglob('*'))
    put(OUT/'packet-seal.json',{'schema':1,'scope':'Contract/model only; includes every owned file and nested receipt except this self-seal',
        'files':{str(p.relative_to(ROOT)):entry(p) for p in sorted(files)}})
    print(json.dumps(message))

if __name__=='__main__': main()
