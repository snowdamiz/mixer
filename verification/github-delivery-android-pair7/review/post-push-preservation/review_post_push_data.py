import sys
ROOT = '/Users/andreyyurlov/Documents/dev/mixer/verification/github-delivery-android-pair7/'
REPO_PREFIX = '/Users/andreyyurlov/Documents/dev/mixer/'
def guard(event,args):
    if event=='import' and args[0].split('.')[0] in ('subprocess','socket','ctypes','signal','select','selectors','asyncio','multiprocessing','threading','pty','http','urllib','ssl','resource','mmap'):
        raise RuntimeError('DENY active module import: '+args[0])
    if event.startswith('os.') and event not in ('os.listdir','os.scandir','os.walk'):
        raise RuntimeError('DENY active OS API: '+event)
    if event.startswith(('subprocess.','socket.','ctypes.','pty.','ssl.','http.','urllib.','signal.','mmap.')):
        raise RuntimeError('DENY active API: '+event)
    if event=='open':
        path,mode,flags=args
        if isinstance(path,int):raise RuntimeError('DENY fd open')
        p=str(path)
        if mode is None:
            if flags not in (0,524288):raise RuntimeError('DENY non-read open flags')
        elif not isinstance(mode,str) or any(c in mode for c in 'wax+'):raise RuntimeError('DENY file mutation')
        if not ((p.startswith(REPO_PREFIX) and '/.git/' not in p) or p.startswith(sys.base_prefix+'/lib/')):
            raise RuntimeError('DENY file read: '+p)
    if event=='exec':
        filename=args[0].co_filename;caller=sys._getframe(1).f_code
        generated=filename=='<string>' and caller.co_filename.startswith(sys.base_prefix+'/lib/') and caller.co_name=='namedtuple'
        if not (filename.startswith(sys.base_prefix+'/lib/') or filename.startswith('<frozen ') or generated):
            raise RuntimeError('DENY subject execution: '+filename)
sys.addaudithook(guard)

import ast
import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from datetime import datetime

REPO=Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT=REPO/'verification/github-delivery-android-pair7'
BASE='3da0d01bd05565a6aad905997beddf6805826241'
BASE_TREE='89297f81773cad23c94ebba1560deccda99c551f'
HEAD='a3967100c5773685bbaedb964aa6e5de9838cb8a'
TREE='69178bebcc6f73680b28e920d798c032a51037f6'
NEW_SCOPE='verification/pair7-java-compile-ci-source-review/'
URL='https://github.com/snowdamiz/mixer.git'
CACHE={}
READ_ROWS={}
TOTAL=0
def read(path):
    global TOTAL
    path=Path(path);key=str(path)
    if key not in CACHE:
        st=path.lstat()
        assert stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode),key
        with path.open('rb') as h:raw=h.read(2000001)
        assert len(raw)<=2000000,key
        TOTAL+=len(raw);assert TOTAL<=16000000
        CACHE[key]=raw
        READ_ROWS[key]={'path':str(path.relative_to(REPO)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    return CACHE[key]
def identity(path):
    read(path);return READ_ROWS[str(Path(path))]
def unique(pairs):
    result={}
    for k,v in pairs:
        assert k not in result,('duplicate JSON key',k)
        result[k]=v
    return result
def data(path):return json.loads(read(path),object_pairs_hook=unique)
def exact(row):
    assert identity(REPO/row['path'])=={k:row[k] for k in ('path','bytes','sha256')},row['path']
    return row
def at(value):return datetime.fromisoformat(value.replace('Z','+00:00'))
def raw_rows(raw):
    p=raw.split(b'\0')
    assert p[-1]==b'' and len(p)%2==1
    result=[]
    for i in range(0,len(p)-1,2):
        meta,path=p[i].decode(),p[i+1].decode()
        fields=meta.split()
        assert len(fields)==5 and fields[0].startswith(':') and fields[-1] in ('A','M','D','T')
        result.append({'path':path,'gitRaw':meta})
    return result
def changed(raw):
    result={}
    for item in raw_rows(raw):
        f=item['gitRaw'].split();p=item['path']
        assert f[-1] in ('A','M') and p in SELECTED and p not in result
        result[p]={'oid':f[3],'mode':f[1]}
        assert result[p]==OBJECTS[p]
    return result
def collapsed(raw):
    result=[]
    for item in raw.split(b'\0'):
        if not item:continue
        t=item.decode()
        assert len(t)>3 and t[2]==' ' and not any(c in t[:2] for c in 'RC')
        result.append({'status':t[:2],'path':t[3:]})
    return result

source_review=data(OUT/'source-review.json')
assert identity(OUT/'source-review.json')=={'path':str((OUT/'source-review.json').relative_to(REPO)),'bytes':8742,'sha256':'aaf0c23af463f209ebcda94311d71ca32d7f2f8a7a07bdc4e72649ff9d638801'}
assert source_review['decision']=='accept-exact-android-pair7-delivery-source-and-argv'
for row in [source_review['selection'],source_review['helper'],*source_review['driverSources'],*source_review['argvApprovals'].values()]:exact(row)
for row in source_review['driverSources']:ast.parse(read(REPO/row['path']),filename=row['path'])
S=data(REPO/source_review['selection']['path'])
rows=list(S['selectedRows'])
for row in rows:
    actual=dict(identity(REPO/row['path']));raw=read(REPO/row['path'])
    actual['mode']='100755' if stat.S_IMODE((REPO/row['path']).lstat().st_mode)&0o111 else '100644'
    actual['oid']=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    assert actual==row,row['path']
self_raw=read(REPO/source_review['selection']['path'])
rows.append({**source_review['selection'],'mode':'100755' if stat.S_IMODE((REPO/source_review['selection']['path']).lstat().st_mode)&0o111 else '100644',
             'oid':hashlib.sha1(b'blob '+str(len(self_raw)).encode()+b'\0'+self_raw).hexdigest()})
SELECTED={r['path'] for r in rows};AUTHORED=sorted(SELECTED)
OBJECTS={r['path']:{'oid':r['oid'],'mode':r['mode']} for r in rows}
assert len(rows)==len(SELECTED)==202
assert hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()==source_review['validation']['selectedRowsIncludingSelfSHA256']
assert not any(p.startswith(NEW_SCOPE.rstrip('/')+'/') for p in SELECTED)
authority_path=OUT/'authority-snapshot-pair7-delivery.json'
authority_row=identity(authority_path)
assert authority_row['bytes']==3392 and authority_row['sha256']=='8aa885308fb5525eaf30b0c38f612b331821c52c2907e473674a8e170d292c23'
A=data(authority_path)
assert A['schema']==1 and A['authorized'] is True and A['phase']=='pair7-delivery' and A['phaseLimit']==1
assert A['baseline']=={'head':BASE,'tree':BASE_TREE} and A['selection']==source_review['selection']
assert A['helper']==source_review['helper'] and A['driverSources']==source_review['driverSources']
assert A['sourceReview']==identity(OUT/'source-review.json')
assert A['stageLimit']==A['commitLimit']==A['nonforcePushLimit']==1 and A['manualWorkflowDispatchLimit']==0
assert A['retryRerunFallbackAllowed'] is A['oldDriverReplayAllowed'] is False
assert A['argvApproval']==source_review['argvApprovals']['pair7-delivery']
assert A['admissionAdapter']=={'exactReadOnlyException':['git','remote','get-url','--push','--all','origin'],
 'allOtherVectorsUseUnchangedHelperValidation':True,'strictManifestEqualityBeforeAdapter':True,
 'custodyStartupKernelWaitEOFSignalLogicChanged':False}
accepted=A['acceptedPreflight']
for row in [accepted['seal'],*accepted['rows']]:exact(row)
pre_root=data(REPO/accepted['seal']['path'])
assert pre_root['decision']=='accept-exact-fresh-pair7-preflight' and pre_root['rows']==accepted['rows']
pre=data(OUT/'preflight-pair7.json')
pres=data(OUT/'preservation-pair7-local.json')
manifest_receipt=data(OUT/'manifest-pair7.json')
assert manifest_receipt['members']==rows and manifest_receipt['paths']==202
assert manifest_receipt['bytes']==sum(r['bytes'] for r in rows)==6605419
assert pre['head']==BASE and pre['tree']==BASE_TREE and pre['indexEmpty'] is True
assert pre['collapsedUntrackedEntries']==2435
M=data(REPO/A['argvApproval']['path'])
assert M['phase']=='pair7-delivery' and len(M['commands'])==23
assert M['session']=={'seconds':240,'count':23,'prefix':'pair7-delivery-'}
names=set(os.listdir(OUT))
labels=['pair7-delivery-'+c['name'] for c in M['commands']]
for suffix in ('.plan.json','.started.json','.admission.json','.command.json','.stdout','.stderr'):
    assert {n for n in names if n.startswith('pair7-delivery-') and n.endswith(suffix)}=={n+suffix for n in labels}
assert 'delivery-pair7-receipt.json' not in names and 'preservation-pair7-after-local.json' not in names
assert not any(n.startswith('pair7-engine-ci-binding-') and n.endswith('.command.json') for n in names)
records={};record_rows=[];all_artifacts=[];aggregate=0;pids=[];first=None;last=None
for ordinal,item in enumerate(M['commands'],1):
    label='pair7-delivery-'+item['name']
    plan=data(OUT/(label+'.plan.json'));started=data(OUT/(label+'.started.json'))
    admission=data(OUT/(label+'.admission.json'));record=data(OUT/(label+'.command.json'))
    argv=[t.replace('{COMMITTED_SHA}',HEAD) for t in item['effectiveArgv']]
    assert record['argv']==plan['argv']==admission['argv']==argv
    assert plan['cwd']==str(REPO) and plan['ordinal']==ordinal and plan['sessionCommandLimit']==23
    assert 0<plan['activeSeconds']<=(45 if item['name']=='push' else 25)
    assert plan['admissionSeconds']==5 and plan['cleanupSeconds']==6
    assert plan['streamCapEachBytes']==8388608 and plan['aggregateCapBytes']==33554432
    assert plan['freshSessionRequired'] is plan['targetReleaseAfterPersistedAdmissionOnly'] is plan['isolatedNoSiteBytecodeDisabled'] is True
    assert plan['nativeSIGCHLD']=={'platform':'darwin-64','handler':None,'flags':0,'SA_NOCLDWAIT':32,'sigactionBytes':16,'readOnly':True}
    pid=record['ownedPID'];pids.append(pid)
    assert type(pid) is int and pid>0
    assert started['ownedPID']==pid and started['targetReleased'] is False
    assert record['identity']==admission['identity']=={'pid':pid,'pgid':pid,'sid':pid}
    assert record['ownedPGID']==admission['parentObservedPGID']==admission['parentObservedSID']==pid
    assert admission['targetReleasedOnlyAfterPersistedAdmission'] is True
    assert admission['activeSeconds']==plan['activeSeconds'] and admission['cleanupSeconds']==6 and admission['streamCapEachBytes']==8388608
    assert at(plan['at'])<=at(started['at'])<=at(admission['at'])<=at(record['at'])
    if first is None:first=at(plan['at'])
    last=at(record['at'])
    for field in ('admitted','directChildReaped','ownedGroupAbsent','wnowaitSupported','terminalObservedWithoutReap',
                  'signalAuthorityRetired','finalReapAttempted','implicitPopenReapingDisabled',
                  'unresolvedChildRetainedUntilIsolatedDriverExit','interpreterExitIsNotCustodyEvidence',
                  'noSignalAfterFinalReapOrLostAuthority','stdoutEOF','stderrEOF','separateOutputPipes'):
        assert record[field] is True,(label,field)
    assert record['exit']==record['rawWaitStatus']==0 and record['rawWaitPID']==pid
    assert record['terminalObservation']==[1,0] and record['postReapAbsenceProbeCount']==1
    assert record['postReapProbeSuccessOrEPERMHeldWithoutRetry'] is False
    assert record['signalAuthorityLost'] is record['stopReason'] is record['failure'] is None
    assert record['signals']==[] and record['sensitiveOutputRejected'] is False
    assert record['authoritySHA256']==authority_row['sha256']
    for stream in ('stdout','stderr'):
        assert record[stream]['path']==str((OUT/(label+'.'+stream)).relative_to(REPO))
        exact(record[stream]);raw=read(REPO/record[stream]['path'])
        assert len(raw)==record[stream+'ObservedBytes']<=8388608
        assert not any(marker in raw.lower() for marker in (b'x-amz-signature=',b'x-goog-signature=',b'ghp_',b'github_pat_',b'authorization: bearer ',b'-----begin private key-----'))
        aggregate+=len(raw)
    assert record['aggregateOutputBytes']==aggregate<=33554432
    records[item['name']]=record
    record_rows.append(identity(OUT/(label+'.command.json')))
    all_artifacts.extend(identity(OUT/(label+suffix)) for suffix in ('.plan.json','.started.json','.admission.json','.command.json','.stdout','.stderr'))
assert len(records)==len(pids)==len(set(pids))==23
assert (last-first).total_seconds()<240
assert [c['name'] for c in M['commands'] if c['kind']=='mutation']==['stage','commit','push']
def output(name,stream='stdout'):return read(REPO/records[name][stream]['path'])
assert output('head').decode().splitlines()==[BASE,BASE_TREE]
assert output('branch')==b'main\n'
assert output('origin').decode().strip()==pre['origin']==URL
for name in ('push-url-before-stage','push-url-prepush','push-url-postpush'):
    assert output(name).decode().splitlines()==[URL]
for name in ('remote-before','remote-prepush'):assert output(name).decode().split()==[BASE,'refs/heads/main']
assert output('remote-postpush').decode().split()==[HEAD,'refs/heads/main']
assert output('committed-head').decode().splitlines()==[HEAD,TREE,BASE]
assert records['committed-head']['argv'][-1]=='HEAD^@'
assert output('index-before')==output('index-after')==b''
assert raw_rows(output('before-diff'))==pres['completeWorktreeRawRows']
assert hashlib.sha256(output('before-diff')).hexdigest()==pres['completeWorktreeRawSHA256']
outside=[r for r in raw_rows(output('before-diff')) if r['path'] not in SELECTED]
assert len(outside)==2 and outside==pres['otherDirtyTracked']
assert raw_rows(output('staged-diff'))==raw_rows(output('after-diff'))==outside
index={}
for entry in output('index-selected').split(b'\0'):
    if not entry:continue
    meta,path=entry.split(b'\t',1);fields=meta.decode().split();path=path.decode()
    assert len(fields)==3 and fields[2]=='0' and path not in index and path in SELECTED
    index[path]={'mode':fields[0],'oid':fields[1]}
assert index==OBJECTS and data(OUT/'selected-index-objects-pair7-local.json')==OBJECTS
cached=changed(output('staged-objects'));parent=changed(output('committed-objects'))
assert cached and cached==parent
assert output('staged-objects')==output('committed-objects')
assert data(OUT/'changed-index-objects-pair7-local.json')==data(OUT/'committed-objects-pair7.json')==cached
assert not any(p.startswith(NEW_SCOPE) for p in cached)
assert read(OUT/'paths-pair7.nul')==b''.join(p.encode()+b'\0' for p in AUTHORED)
formatting=[p for p in AUTHORED if p not in {r['path'] for r in S['formattingExclusions']}]
assert len(formatting)==197 and len(S['formattingExclusions'])==5
argv=records['authored-check']['argv'];assert argv[argv.index('--')+1:]==formatting
assert output('authored-check')==output('authored-check','stderr')==b''
for name in ('pair7-delivery-once.json','pair7-stage-once.json','pair7-commit-once.json','pair7-push-once.json'):
    assert name in names
stage=data(OUT/'pair7-stage-once.json');commit=data(OUT/'pair7-commit-once.json');push=data(OUT/'pair7-push-once.json')
assert stage['stageLimit']==commit['commitLimit']==1 and stage['retryAllowed'] is commit['retryAllowed'] is False
assert commit['parentMustEqual']==BASE and push['head']==HEAD and push['tree']==TREE and push['parent']==BASE
assert push['force'] is False and push['reservationConsumedBeforeSubmit'] is True and push['retryOnUnknownOutcome'] is False
for name,res in [('stage',stage),('commit',commit),('push',push)]:
    assert at(res['at'])<=at(data(OUT/('pair7-delivery-'+name+'.plan.json'))['at'])
for expected in pres['tracked']+pres['protectedSnapshots']:
    actual=identity(REPO/expected['path'])
    assert actual=={k:expected[k] for k in ('path','bytes','sha256')}
    st=(REPO/expected['path']).lstat()
    assert stat.S_IMODE(st.st_mode)==expected['mode']==0o644
    assert stat.S_IFMT(st.st_mode)==expected['type']==stat.S_IFREG
assert pres['tracked']==pres['protectedSnapshots'] and len(pres['tracked'])==2
before=pres['statusCollapsed'];after=collapsed(output('collapsed-status-after'))
prior=[r['path'] for r in before if r['status']=='??'];current=[r['path'] for r in after if r['status']=='??']
assert len(before)==2449 and len(after)==2427 and len(prior)==2435 and len(current)==2425
def projected(path):
    path=path.rstrip('/')
    return any(p==path or p.startswith(path+'/') for p in SELECTED)
def covered(path,old):return path==old or old.endswith('/') and path.startswith(old)
old_outside=[r for r in before if r['status']!='??' and r['path'] not in SELECTED]
new_outside=[r for r in after if r['status']!='??' and r['path'] not in SELECTED]
assert old_outside==new_outside and len(old_outside)==2
unrelated=[p for p in current if not projected(p) and not any(covered(p,old) for old in prior)]
missing=[old for old in prior if not projected(old) and not any(covered(p,old) or covered(old,p) for p in current)]
assert unrelated==[NEW_SCOPE] and missing==[]
assert len(set(prior)&set(current))==2423
assert len(set(prior)-set(current))==12 and len(set(current)-set(prior))==2
assert len(pres['untrackedCollapsed'])==2435
for expected in pres['untrackedCollapsed']:
    st=(REPO/expected['path'].rstrip('/')).lstat()
    assert {'path':expected['path'],'mode':stat.S_IMODE(st.st_mode),'type':stat.S_IFMT(st.st_mode),
            'inode':st.st_ino,'device':st.st_dev}==expected
st=(REPO/NEW_SCOPE.rstrip('/')).lstat()
new_scope_metadata={'path':NEW_SCOPE,'type':stat.S_IFMT(st.st_mode),'mode':stat.S_IMODE(st.st_mode),'inode':st.st_ino,'device':st.st_dev}
assert new_scope_metadata=={'path':NEW_SCOPE,'type':16384,'mode':493,'inode':171885823,'device':16777233}
wr=(REPO/'.wrangler').lstat()
assert wr.st_ino==134689423 and wr.st_dev==16777233 and stat.S_IMODE(wr.st_mode)==pres['wrangler']['mode']
try:(REPO/'hosted/lib/mixer_hosted/artifacts/store.ex').lstat()
except FileNotFoundError:pass
else:raise AssertionError('artifact store unexpectedly exists')
history=data(REPO/S['historicalClosure']['path']);exact(S['historicalClosure'])
assert history['closedCommandSeries']['total']==109
for row in history['rows']:exact(row)
workflow=exact(S['ordinaryHost']['source'])
assert workflow['bytes']==31363 and workflow['sha256']=='5ce51236f178080e3301289513fa3f5a8313e3a3969b0bab3f2b1cd4668de7f5'
assert S['ordinaryHost']['workflowID']==393488255
common=read(OUT/'selection_common_android_pair7.py').decode()
driver=read(OUT/'deliver_android_pair7.py').decode()
binder=read(OUT/'bind_engine_ci_android_pair7.py').decode()
assert driver.splitlines()[91]=="collapsed_proof = compare_collapsed(preservation['statusCollapsed'], after)"
assert "assert selected_projection(value) or any(covered(value, old) for old in prior)" in common
assert "c.complete(); check_sources()" in driver
assert driver.index('collapsed_proof = compare_collapsed')<driver.index("save('preservation-pair7-after-local.json'")<driver.index('c.complete(); check_sources()')
assert driver.index('c.complete(); check_sources()')<driver.index("save('delivery-pair7-receipt.json'")
assert "r = json.loads((OUT / 'delivery-pair7-receipt.json').read_bytes())" in binder
assert "assert r['pushed'] is True and r['force'] is False and r['parent'] == BASE and r['indexEmpty'] is True" in binder
assert "assert r['selection'] == row(ROOT / SELECTION)" in binder
assert "assert c.run('head').decode().splitlines() == [head, r['tree']]" in binder
assert "assert a['acceptedDelivery'] == row(OUT / 'delivery-pair7-receipt.json')" in common
assert "self.authority_row['sha256'] == owned.authority()" in common
summary={
 'status':'VERIFIED_GIT_EFFECTS_AND_NARROW_ROOT_RECOVERY_PRECONDITIONS',
 'head':HEAD,'tree':TREE,'soleParent':BASE,'selection':source_review['selection'],
 'deliveryAuthority':authority_row,'sourceReview':identity(OUT/'source-review.json'),
 'deliveryCommandCount':23,'allDeliveryExitZeroRawWaitZeroAndCustodyClosed':True,'ownedPIDsDistinct':23,'signals':0,
 'typedVectorsAuthoritiesAndAllPlanStartAdmissionTerminalStreamRowsMatch':True,
 'onlyMutations':['stage','commit','push'],'manualWorkflowCommands':0,'replays':0,
 'selectedPaths':202,'selectedBytes':6605419,'selectedIndexObjects':len(index),'cachedChangedObjects':len(cached),
 'parentChangedObjects':len(parent),'unchangedSelectedObjects':202-len(cached),
 'allSelectedSourceSHA256BytesOIDModesMatch':True,'noOutsideSelectedCommittedPaths':True,
 'soleParentHEADAllParentsCardinality':True,'nonforcePushRemoteAndURLProofsMatch':True,'indexAfterStoredOutputEmpty':True,
 'defaultWhitespacePaths':197,'exactImmutableWhitespaceExceptions':5,
 'outsideSelectedDirtyProtectedFiles':2,'protectedByteModesMatch':True,'originalCollapsedIdentitiesPreserved':2435,
 'collapsedStatusRowsBefore':2449,'collapsedStatusRowsAfter':2427,'untrackedEntriesBefore':2435,'untrackedEntriesAfter':2425,
 'commonUntrackedPaths':2423,'priorCollapsedScopesNoLongerListed':12,'newlyListedEntries':2,
 'priorCollapsedScopesNoLongerListedPaths':sorted(set(prior)-set(current)),
 'newlyListedEntryPaths':sorted(set(current)-set(prior)),
 'newEntriesWithinPriorScope':1,'unexplainedMissingPriorScopes':0,
 'originalStrictComparatorPassed':False,'originalStrictComparatorNewUnrelatedEntries':unrelated,
 'newAuthorizedConcurrentNamespaceReportedByRoot':new_scope_metadata,
 'newNamespaceExcludedFromStageAndCommit':True,
 'recursiveUntrackedContentProof':False,'allCleanTrackedFilesIndependentlyHashed':False,
 'helperSourceAndSelectionUnchanged':True,'wranglerIdentityMatches':True,'artifactStoreAbsent':True,'historicalClosedCommands':109,
 'driverProducedDeliveryReceiptExists':False,'driverPostPreservationReceiptExists':False,'driverCompleteTailReached':False,
 'originalDriverFailureReportedByRoot':{'session':33963,'outerExit':1,'source':'deliver_android_pair7.py:92 / selection_common_android_pair7.py:127','reason':'New unrelated collapsed entry '+NEW_SCOPE},
 'binderExpectedReceiptPath':'verification/github-delivery-android-pair7/delivery-pair7-receipt.json',
 'binderMinimumReceiptFields':['pushed','force','parent','indexEmpty','selection','head','tree'],
 'binderRequiresDriverProducerIdentity':False,
 'binderPhaseAuthorityRequiresExactAcceptedDeliveryRowAtExpectedPath':True,
 'sameBinderSourceMechanicallyAcceptsExplicitRootAuthoredRecoveredData':True,
 'automaticDriverSuccessMayBeClaimed':False,
 'recoveryRequiresSeparateRootDecisionAndReceiptWithExplicitFailureAndExactNamespaceProvenance':True,
 'newTargetCommandsNecessaryToReconstructTheseEffects':0,
 'aggregateDeliveryOutputBytes':aggregate,'recordedDeliverySpanSeconds':(last-first).total_seconds(),
 'commandRecordRowsSHA256':hashlib.sha256(json.dumps(record_rows,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'planAdmissionTerminalStreamRowsSHA256':hashlib.sha256(json.dumps(sorted(all_artifacts,key=lambda r:r['path']),sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'readSetRowsSHA256':hashlib.sha256(json.dumps(sorted(READ_ROWS.values(),key=lambda r:r['path']),sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'readFiles':len(READ_ROWS),'readBytes':TOTAL,'fileReadBound':2000000,'aggregateReadBound':16000000,
 'checkerPython':sys.version,'checkerInterpreter':sys.executable,
 'reviewerHelperOrSubjectImportedOrExecuted':False,'reviewerTargetCommandsExecuted':0,'reviewerActiveAPIProcessNetworkNativeCompilerActions':0,
 'authorityGranted':False}
print(json.dumps(summary,indent=2))

