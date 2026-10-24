#!/usr/bin/env python3
"""Seal the bounded V3 source/host pass after verified synthetic archival."""
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
PACKET=ROOT/'verification/apple-toggle-keyboard-full-case-preparation-v3'
DOC=ROOT/'docs/apple-toggle-keyboard-full-case-independent-review-v3.md'
EXPECTED='2d600f0289324591cfab82b3ff3d0d987dcdfce9e081a0ff2571d47d6c844039'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):(HERE/name).write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')

assert not (HERE/'review-seal.json').exists(),'Independent review is immutable after seal'
assert sha(PACKET/'packet-seal.json')==EXPECTED
commands=json.loads((HERE/'commands.json').read_bytes());assert commands['allCommandsSucceeded']
for name in ['allocation-failure.json','cleanup-failure-reproduction.json']:assert json.loads((HERE/name).read_bytes())['repaired']
assert json.loads((HERE/'preloaded-durable.json').read_bytes())['rejectedBeforeHarnessImport']
argv=[sys.executable,'-B',str(PACKET/'verify_isolated.py')];start=time.monotonic()
p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,timeout=60)
(HERE/'final-verify.stdout').write_text(p.stdout);(HERE/'final-verify.stderr').write_text(p.stderr)
write('final-verify.json',dict(argv=argv,cwd=str(ROOT),exitCode=p.returncode,elapsedSeconds=time.monotonic()-start,
    stdoutSHA256=sha(HERE/'final-verify.stdout'),stderrSHA256=sha(HERE/'final-verify.stderr')))
assert p.returncode==0,p.stderr

copies={}
for folder,name in [('apple-toggle-keyboard-focus-v9-preparation',v) for v in ['settings_telemetry.py','durable_settings.py','keyboard_oracle.py']]+[('apple-toggle-keyboard-focus',v) for v in ['keyboard_bridge.py','keyboard_oracle.py']]+[('apple-toggle-pan-commit-harness-v2','observation_reader.py')]:
    fresh=PACKET/'inputs/runtime/verification'/folder/name;old=ROOT/'verification'/folder/name
    assert sha(fresh)==sha(old)
    copies[str(fresh.relative_to(ROOT))]=dict(sha256=sha(fresh),historicalSHA256=sha(old),exactCopy=True)
v1=ROOT/'verification/apple-toggle-keyboard-full-case-preparation'
for fresh in sorted((PACKET/'harness').rglob('*')):
    if fresh.is_file():assert sha(fresh)==sha(v1/'harness'/fresh.relative_to(PACKET/'harness'))
old=(ROOT/'verification/apple-toggle-keyboard-focus/harness/UITests/ToggleUITests.swift').read_text()
fresh=(PACKET/'harness/UITests/ToggleUITests.swift').read_text()
assert old[old.index('    private func launchCase('):old.rfind('\n}')] in fresh
assert old[old.index('    private func bridge('):old.index('    private func settingsObservation(')] in fresh
v2=ROOT/'verification/apple-toggle-keyboard-full-case-preparation-v2'
delta=''.join(difflib.unified_diff((v2/'orchestration.py').read_text().splitlines(keepends=True),(PACKET/'orchestration.py').read_text().splitlines(keepends=True),fromfile=str((v2/'orchestration.py').relative_to(ROOT)),tofile=str((PACKET/'orchestration.py').relative_to(ROOT))))
assert delta==(PACKET/'v3-runtime.delta.diff').read_text()
contract=json.loads((PACKET/'private-contract.json').read_bytes())
assert contract['unchangedBudgets']==json.loads((v1/'private-contract.json').read_bytes())['unchangedBudgets']
selection=json.loads((PACKET/'runtime-selection.json').read_bytes())
write('source-contract.json',dict(exactCopies=copies,wholeRunnerTreeExactToV1=True,allSixOriginalAppHelpersAndMethodsExact=True,
    originalAppBridgeBlockExact=True,orchestrationDeltaExactlyRecomputed=True,allOriginalBudgetValuesUnchanged=True,
    selectedSources=sum(name.endswith('.py') for name in selection['files']),selectedData=sum(name.endswith('.json') for name in selection['files']),
    producerInputBindingCount=len(json.loads((PACKET/'input-bindings.json').read_bytes())),producerSealSHA256=EXPECTED,
    runnerSourceTreeSHA256=json.loads((PACKET/'provenance.json').read_bytes())['runnerSourceTreeSHA256'],
    sourceRevisionContext='67d6d0455c64ccb454c2e06e11edbdca2836a1cd',sourceRevisionContextMeaning='Inherited producer metadata only; no Git query'))

history={}
protected=[('apple-toggle-keyboard-full-case-preparation','packet-seal.json','1e6a0f82dcb65f035abfc8eca3bb7bbe332b1a265553295773e10855276fb8f9'),
    ('apple-toggle-keyboard-full-case-independent-review','review-seal.json','6693e3a4b17768befb418af498e30d06259e7a3c2e3b81c0895540bd7eab4f33'),
    ('apple-toggle-keyboard-full-case-preparation-v2','packet-seal.json','3a17071cc13bada8e47c48d2b739289ac9210ecacb90935e016a1ea4ce5a14d4'),
    ('apple-toggle-keyboard-full-case-independent-review-v2','review-addendum-seal.json','f574fb107be4bdb79d0a10b433864dcbc3fc005f2c69f63cf06f94826c2e6a60')]
for folder,name,expected in protected:
    path=ROOT/'verification'/folder/name;assert sha(path)==expected
    files=json.loads(path.read_bytes())['files'];assert all(sha(ROOT/name)==digest for name,digest in files.items())
    history[folder]=dict(selectedSeal=name,sealSHA256=expected,boundFiles=len(files),allUnchanged=True)
write('protected-history.json',history)

scratch=HERE/'scratch';members={};http_files=0;requests=0
for path in sorted(scratch.rglob('*')):
    assert not path.is_symlink()
    info=path.stat();name=str(path.relative_to(scratch))
    if path.is_dir():members[name]=dict(kind='directory',mode=stat.S_IMODE(info.st_mode))
    else:
        assert path.is_file();members[name]=dict(kind='file',mode=stat.S_IMODE(info.st_mode),bytes=info.st_size,sha256=sha(path))
        if path.name=='http-receipts.json':http_files+=1;requests+=len(json.loads(path.read_bytes()))
archive=HERE/'synthetic-host-evidence.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for name,row in members.items():
        info=tarfile.TarInfo(name);info.mode=row['mode']
        if row['kind']=='directory':info.type=tarfile.DIRTYPE;tar.addfile(info)
        else:data=(scratch/name).read_bytes();info.size=len(data);tar.addfile(info,io.BytesIO(data))
with tarfile.open(archive,'r:gz') as tar:
    seen=set()
    for member in tar:
        row=members[member.name];assert member.name not in seen and member.mode==row['mode'];seen.add(member.name)
        if row['kind']=='directory':assert member.isdir()
        else:
            assert member.isfile() and member.size==row['bytes']
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==row['sha256']
    assert seen==set(members)
write('synthetic-host-evidence-manifest.json',dict(archiveSHA256=sha(archive),members=members,byteAndModeVerified=True,
    syntheticHTTPReceiptFiles=http_files,syntheticHTTPRequests=requests))
shutil.rmtree(scratch);assert not scratch.exists()
before=json.loads((HERE/'producer-inputs-before.json').read_bytes())
after={name:sha(ROOT/name) for name in before};assert before==after
write('producer-inputs-final.json',after)
write('cleanup.json',dict(ownedSyntheticScratchArchived=True,archiveBytesAndModesVerified=True,ownedSyntheticScratchAbsent=True,
    allOwnedLoopbackThreadsJoined=True,allOwnedLoopbackServersClosed=True,controlledFaultEntriesRecordedBeforeNarrowRecovery=True,
    controlledFaultEntriesAbsent=True,protectedFixturesPreserved=True,producerAndHistoricalSealsUnchanged=True,
    nativeInstancesQueried=False,nativeInstancesCreated=False,nativeProcessesLaunched=False,physicalPhones='disconnected-deferred'))
write('review.json',dict(schema='mixer.apple-toggle.keyboard-full-case-independent-review.1',status='independent-source-host-review-passed',
    producerSealSHA256=EXPECTED,producerSealedFiles=80,sourceHostReviewPassed=True,rootAcceptancePending=True,
    originalTwoFindingsRepaired=True,allocationFindingRepaired=True,actionableFindings=[],
    retainedOracleMethods=9,retainedBridgeWitnessMethods=4,portedIndependentMethods=13,reportingAndProvenanceRepairMethods=10,
    exactAllocationProbeMethods=1,adjacentAllocationMethods=8,totalPassingHostMethods=45,closedAliasPreloadControls=24,
    normalAndDuplicateImportClosureMatched=True,selectedSourceFiles=22,selectedCaseDataFiles=3,actualLoadedSourceFiles=21,actualImportDataReads=4,
    producerInputBindings=2537,syntheticHTTPRequests=requests,commandsPassed=True,futureCompileAndRunSelected=False,
    runnerCompiled=False,nativeExecuted=False,nativeInstancesQueried=False,allSixNativeApplicationCasesPending=True,
    nativeKeyboardQualification=False,carrierAccepted=False,gaAccepted=False,physicalPhones='disconnected-deferred'))
files={str(path.relative_to(ROOT)):sha(path) for path in sorted(HERE.rglob('*')) if path.is_file()};files[str(DOC.relative_to(ROOT))]=sha(DOC)
write('review-seal.json',dict(schema='mixer.apple-toggle.keyboard-full-case-independent-review-seal.1',
    observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='independent-source-host-review-passed',producerSealSHA256=EXPECTED,
    files=files,sourceHostReviewPassed=True,rootAcceptancePending=True,futureCompileAndRunSelected=False,nativeAcceptance=False,carrierAccepted=False,gaAccepted=False))
print(json.dumps(dict(status='independent-source-host-review-passed',files=len(files),sealSHA256=sha(HERE/'review-seal.json'),
    hostMethods=45,closedAliasControls=24,syntheticHTTPRequests=requests)))
