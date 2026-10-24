#!/usr/bin/env python3
"""Seal a failed independent source/host review; archive before scratch cleanup."""
import datetime
import difflib
import hashlib
import io
import json
import pathlib
import shutil
import stat
import subprocess
import sys
import tarfile
import time

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PACKET=ROOT/'verification/apple-toggle-keyboard-full-case-preparation-v2'
DOC=ROOT/'docs/apple-toggle-keyboard-full-case-independent-review-v2.md'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
EXPECTED='3a17071cc13bada8e47c48d2b739289ac9210ecacb90935e016a1ea4ce5a14d4'

assert not (HERE/'review-seal.json').exists(),'Review is immutable after sealing'
commands=json.loads((HERE/'commands.json').read_bytes())
assert commands['allCommandsSucceeded']
assert json.loads((HERE/'cleanup-failure-reproduction.json').read_bytes())['repaired']
assert json.loads((HERE/'preloaded-durable.json').read_bytes())['rejectedBeforeHarnessImport']
assert json.loads((HERE/'allocation-failure.json').read_bytes())['reproduced']
assert sha(PACKET/'packet-seal.json')==EXPECTED

argv=[sys.executable,'-B',str(PACKET/'verify_isolated.py')]
started=time.monotonic();p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,timeout=60)
(HERE/'final-verify.stdout').write_text(p.stdout);(HERE/'final-verify.stderr').write_text(p.stderr)
write(HERE/'final-verify.json',dict(argv=argv,cwd=str(ROOT),exitCode=p.returncode,elapsedSeconds=time.monotonic()-started,
    stdoutSHA256=sha(HERE/'final-verify.stdout'),stderrSHA256=sha(HERE/'final-verify.stderr')))
assert p.returncode==0,p.stderr

source_checks={}
for folder,name in [('apple-toggle-keyboard-focus-v9-preparation',v) for v in ['settings_telemetry.py','durable_settings.py','keyboard_oracle.py']]+[('apple-toggle-keyboard-focus',v) for v in ['keyboard_bridge.py','keyboard_oracle.py']]+[('apple-toggle-pan-commit-harness-v2','observation_reader.py')]:
    snap=PACKET/'inputs/runtime/verification'/folder/name;historical=ROOT/'verification'/folder/name
    source_checks[str(snap.relative_to(ROOT))]=dict(sha256=sha(snap),historicalSHA256=sha(historical),exactCopy=sha(snap)==sha(historical))
for name in ['DiagnosticTransport.swift','PublicSwitchSelection.swift']:
    fresh=PACKET/'harness/UITests'/name;old=ROOT/'verification/apple-toggle-keyboard-focus-v7-preparation/harness/UITests'/name
    source_checks[str(fresh.relative_to(ROOT))]=dict(sha256=sha(fresh),historicalSHA256=sha(old),exactCopy=sha(fresh)==sha(old))
assert all(row['exactCopy'] for row in source_checks.values())
old=(ROOT/'verification/apple-toggle-keyboard-focus/harness/UITests/ToggleUITests.swift').read_text()
new=(PACKET/'harness/UITests/ToggleUITests.swift').read_text()
app_block=old[old.index('    private func launchCase('):old.rfind('\n}')]
bridge_block=old[old.index('    private func bridge('):old.index('    private func settingsObservation(')]
assert app_block in new and bridge_block in new
v7=ROOT/'verification/apple-toggle-keyboard-focus-v7-preparation/harness/UITests/ToggleUITests.swift'
fresh=PACKET/'harness/UITests/ToggleUITests.swift'
delta=''.join(difflib.unified_diff(v7.read_text().splitlines(keepends=True),fresh.read_text().splitlines(keepends=True),fromfile=str(v7.relative_to(ROOT)),tofile='verification/apple-toggle-keyboard-full-case-preparation/harness/UITests/ToggleUITests.swift'))
assert delta==(PACKET/'runner-source.delta.diff').read_text()
write(HERE/'source-contract.json',dict(exactCopies=source_checks,allSixOriginalAppHelpersAndMethodsExact=True,
    originalAppBridgeBlockExact=True,deltaDiffExactlyRecomputed=True,producerSealSHA256=EXPECTED,
    producerInputBindingCount=len(json.loads((PACKET/'input-bindings.json').read_bytes())),
    runnerSourceTreeSHA256=json.loads((PACKET/'provenance.json').read_bytes())['runnerSourceTreeSHA256'],
    sourceRevisionContext=commands.get('sourceRevisionContext','67d6d0455c64ccb454c2e06e11edbdca2836a1cd'),
    sourceRevisionContextMeaning='Inherited producer label only; no Git query'))

scratch=HERE/'scratch';members={};http_requests=0;http_files=0
for path in sorted(scratch.rglob('*')):
    assert not path.is_symlink()
    info=path.stat();name=str(path.relative_to(scratch))
    if path.is_dir():members[name]=dict(kind='directory',mode=stat.S_IMODE(info.st_mode))
    else:
        assert path.is_file()
        members[name]=dict(kind='file',mode=stat.S_IMODE(info.st_mode),bytes=info.st_size,sha256=sha(path))
        if path.name=='http-receipts.json':http_files+=1;http_requests+=len(json.loads(path.read_bytes()))
archive=HERE/'synthetic-host-evidence.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for name,row in members.items():
        info=tarfile.TarInfo(name);info.mode=row['mode']
        if row['kind']=='directory':info.type=tarfile.DIRTYPE;tar.addfile(info)
        else:
            data=(scratch/name).read_bytes();info.size=len(data);tar.addfile(info,io.BytesIO(data))
with tarfile.open(archive,'r:gz') as tar:
    seen={}
    for member in tar:
        row=members[member.name];assert member.mode==row['mode']
        if row['kind']=='directory':assert member.isdir()
        else:
            assert member.isfile() and member.size==row['bytes']
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==row['sha256']
        seen[member.name]=row
    assert seen==members
write(HERE/'synthetic-host-evidence-manifest.json',dict(archiveSHA256=sha(archive),members=members,
    byteAndModeVerified=True,syntheticHTTPReceiptFiles=http_files,syntheticHTTPRequestsAcrossRetainedAttempts=http_requests))
shutil.rmtree(scratch)
assert not scratch.exists()
before=json.loads((HERE/'producer-inputs-before.json').read_bytes())
after={name:sha(ROOT/name) for name in before};assert before==after
write(HERE/'producer-inputs-final.json',after)
protected={}
for folder,expected in [('apple-toggle-keyboard-full-case-preparation','1e6a0f82dcb65f035abfc8eca3bb7bbe332b1a265553295773e10855276fb8f9'),('apple-toggle-keyboard-full-case-independent-review','6693e3a4b17768befb418af498e30d06259e7a3c2e3b81c0895540bd7eab4f33')]:
    path=ROOT/'verification'/folder/('packet-seal.json' if folder.endswith('preparation') else 'review-seal.json')
    assert sha(path)==expected
    files=json.loads(path.read_bytes())['files']
    assert all(sha(ROOT/name)==digest for name,digest in files.items())
    protected[folder]=dict(sealSHA256=expected,boundFiles=len(files),allUnchanged=True)
write(HERE/'protected-history.json',protected)
write(HERE/'cleanup.json',dict(ownedSyntheticScratchArchived=True,byteAndModeVerified=True,ownedSyntheticScratchAbsent=True,
    reproducedLeakedServerRecovered=True,reproducedLeakedThreadJoined=True,producerSealedInputsUnchanged=True,
    nativeInstancesQueried=False,nativeInstancesCreated=False,nativeProcessesLaunched=False,physicalPhones='disconnected-deferred'))
write(HERE/'review.json',dict(schema='mixer.apple-toggle.keyboard-full-case-independent-review.1',status='changes-required',
    producerSealSHA256=EXPECTED,producerSealedFiles=77,sourceAccepted=False,independentHostMethods=24,
    retainedOracleMethods=9,retainedBridgeWitnessMethods=4,totalPassingHostMethods=37,closedAliasPreloadControls=23,originalTwoFindingsRepaired=True,
    commandsPassed=True,passingNegativeReproductionsAreDefects=True,
    findings=[dict(id='R3',priority=2,title='Workspace allocation failure leaks owned directory and falsely passes removal',evidence='allocation-failure.json')],
    nativeCompiled=False,nativeExecuted=False,nativeInstancesQueried=False,allSixNativeApplicationCasesPending=True,
    nativeKeyboardQualification=False,carrierAccepted=False,gaAccepted=False,physicalPhones='disconnected-deferred'))
files={str(p.relative_to(ROOT)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}
files[str(DOC.relative_to(ROOT))]=sha(DOC)
write(HERE/'review-seal.json',dict(schema='mixer.apple-toggle.keyboard-full-case-independent-review-seal.1',
    observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='changes-required',
    producerSealSHA256=EXPECTED,files=files,sourceAccepted=False,nativeAcceptance=False,carrierAccepted=False,gaAccepted=False))
print(json.dumps(dict(status='changes-required',files=len(files),sealSHA256=sha(HERE/'review-seal.json'),
    syntheticHTTPRequestsAcrossRetainedAttempts=http_requests,totalPassingHostMethods=37)))
