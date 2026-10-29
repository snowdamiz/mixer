import sys
ROOT = '/Users/andreyyurlov/Documents/dev/mixer/verification/github-delivery-android-pair7/'
REPO_PREFIX = '/Users/andreyyurlov/Documents/dev/mixer/'
def guard(event, args):
    if event == 'import' and args[0].split('.')[0] in ('subprocess','socket','ctypes','signal','select','selectors','asyncio','multiprocessing','threading','pty','http','urllib','ssl','resource','mmap'):
        raise RuntimeError('DENY active module import: ' + args[0])
    if event.startswith('os.') and event not in ('os.listdir','os.scandir','os.walk'):
        raise RuntimeError('DENY active OS API: ' + event)
    if event.startswith(('subprocess.','socket.','ctypes.','pty.','ssl.','http.','urllib.','signal.','mmap.')):
        raise RuntimeError('DENY active API: ' + event)
    if event == 'open':
        path, mode, flags = args
        if isinstance(path,int):
            raise RuntimeError('DENY fd open')
        p = str(path)
        if mode is None:
            if flags not in (0,524288):
                raise RuntimeError('DENY non-read open flags')
        elif not isinstance(mode,str) or any(c in mode for c in 'wax+'):
            raise RuntimeError('DENY file mutation')
        if not ((p.startswith(REPO_PREFIX) and '/.git/' not in p) or p.startswith(sys.base_prefix + '/lib/')):
            raise RuntimeError('DENY file read: ' + p)
    if event == 'exec':
        filename = args[0].co_filename
        caller = sys._getframe(1).f_code
        trusted_generated = filename == '<string>' and caller.co_filename.startswith(sys.base_prefix + '/lib/') and caller.co_name == 'namedtuple'
        if not (filename.startswith(sys.base_prefix + '/lib/') or filename.startswith('<frozen ') or trusted_generated):
            raise RuntimeError('DENY subject source execution: ' + filename)
sys.addaudithook(guard)

import ast
import difflib
import hashlib
import json
import os
import stat
from pathlib import Path

REPO = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT = REPO / 'verification/github-delivery-android-pair7'
OLD = REPO / 'verification/github-delivery-axis-canonical-followup'
REFUSAL = b'raise SystemExit("UNBOUND SOURCE TEMPLATE: exact source/argv review and root materialization are required")\n'
CACHE = {}
TOTAL = 0
def read(path):
    global TOTAL
    path = Path(path)
    if str(path) not in CACHE:
        with path.open('rb') as handle:
            raw = handle.read(200001)
        assert len(raw) <= 200000
        TOTAL += len(raw)
        assert TOTAL <= 2000000
        CACHE[str(path)] = raw
    return CACHE[str(path)]
def identity(path):
    path = Path(path)
    st = path.lstat()
    assert stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode)
    raw = read(path)
    return {'path':str(path.relative_to(REPO)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def unique(pairs):
    result = {}
    for k,v in pairs:
        assert k not in result
        result[k] = v
    return result
def data(path):
    return json.loads(read(path),object_pairs_hook=unique)
def exact(row):
    assert identity(REPO/row['path']) == {k:row[k] for k in ('path','bytes','sha256')},row['path']
    if 'mode' in row:
        mode='100755' if stat.S_IMODE((REPO/row['path']).lstat().st_mode)&0o111 else '100644'
        assert mode==row['mode']
    return row
def normalized(text):
    for a,b in [('axis_canonical_common','android_pair7_common'),('axis_canonical_owned','android_pair7_owned'),
                ('_axis_canonical.py','_android_pair7.py'),('canonical-','pair7-'),('-canonical','-pair7')]:
        text=text.replace(a,b)
    return text
prep_row=identity(OUT/'preparation.json')
assert prep_row['bytes']==10460 and prep_row['sha256']=='fd37f2dd49e7f7b564b3270d752143e179dabb61c951c5f8136c1b9297628247'
P=data(OUT/'preparation.json')
assert len(P['inventory'])==15
inventory=[exact(row) for row in P['inventory']]
inventory.append(prep_row)
assert len({row['path'] for row in inventory})==16
for row in inventory:
    raw=read(REPO/row['path'])
    assert b'\0' not in raw and raw.endswith(b'\n') and not raw.endswith(b'\n\n')
    assert not any(line.endswith((b' ',b'\t')) for line in raw.splitlines()),row['path']
    assert stat.S_IMODE((REPO/row['path']).lstat().st_mode)==0o644
for row in P['sourceInputs']:
    exact(row)
exact(P['historicalClosure'])
exact(P['currentApplicationContext'])
history=data(REPO/P['historicalClosure']['path'])
assert history['baseline']=={'head':'3da0d01bd05565a6aad905997beddf6805826241','tree':'89297f81773cad23c94ebba1560deccda99c551f'}
assert history['closedCommandSeries']=={
 'olderSeries':71,'previousCanonical':{'preflight':10,'delivery':23,'ordinaryEngineBinding':5,'total':38},
 'total':109,'exitZero':108,'historicalOriginalClosedStageExitOne':1,'historicalOriginalClosedStageRawWaitStatus':256}
for row in history['rows']:exact(row)
seal=data(OLD/'review/actual/seal.json')
assert seal['head']==history['baseline']['head'] and seal['tree']==history['baseline']['tree']
assert identity(OLD/'review/actual/seal.json')['sha256']=='0c28c4b69beeb30973fdb000dc767751b752f4be62dd7b1b5e30cef4c08cec1d'
assert seal['combinedLocalCommands']==109 and seal['combinedExitZero']==108
before=read(OLD/'owned.py')
after=read(OUT/'owned.py')
assert len(before)==len(after)==29385
a,b=before.splitlines(keepends=True),after.splitlines(keepends=True)
assert len(a)==len(b) and [i+1 for i,(x,y) in enumerate(zip(a,b)) if x!=y]==[111]
x,y=a[110].split(b"'"),b[110].split(b"'")
changed=[i for i,(p,q) in enumerate(zip(x,y)) if p!=q]
assert len(changed)==2 and all(len(x[i])==len(y[i])==40 for i in changed)
assert b''.join(b[:110]+[a[110]]+b[111:])==before
assert y[changed[0]]==b'3da0d01bd05565a6aad905997beddf6805826241'
assert y[changed[1]]==b'89297f81773cad23c94ebba1560deccda99c551f'
source_rows=[]
for stem in ('preflight','deliver','bind_engine_ci'):
    path=OUT/(stem+'_android_pair7.py.template')
    raw=read(path)
    assert raw.startswith(REFUSAL)
    ast.parse(raw,filename=str(path))
    ast.parse(raw[len(REFUSAL):],filename=str(path)+':exact-guard-removed')
    expected=REFUSAL.decode()+normalized(read(OLD/(stem+'_axis_canonical.py')).decode())
    if stem=='deliver':
        expected=expected.replace("c.run('authored-check')  # All other selected paths; three exact immutable exceptions.",
         "c.run('authored-check')  # Exact root-reviewed formatting subset; all selected object proofs remain mandatory.")
    elif stem=='bind_engine_ci':
        expected=expected.replace("registration['id'] > 0","registration['id'] == 393488255")
    assert raw.decode()==expected,stem
    source_rows.append(identity(path))
common_text=read(OUT/'selection_common_android_pair7.py.template').decode()
assert common_text.startswith(REFUSAL.decode())
nt=ast.parse(common_text)
ast.parse(common_text[len(REFUSAL):],filename='common-exact-first-guard-removed')
old_text=normalized(read(OLD/'selection_common_axis_canonical.py').decode())
ot=ast.parse(old_text)
nf={n.name:n for n in nt.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
of={n.name:n for n in ot.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
assert set(nf)==set(of)
for name in nf:
    if name not in ('check_sources','StrictCommands'):assert ast.dump(nf[name])==ast.dump(of[name]),name
assignments={t.id:n.value for n in nt.body if isinstance(n,ast.Assign) for t in n.targets if isinstance(t,ast.Name)}
for key in ('SELECTION','SELECTION_BYTES','SELECTION_SHA','SELECTED_COUNT','FORMATTING_DECISION_ROW','PUBLIC_CONTROL_OUTPUTS_DECISION_ROW'):
    assert ast.literal_eval(assignments[key]) is None,key
for key in ('FORMATTING_EXCLUSIONS','PUBLIC_CONTROL_OUTPUTS'):
    assert ast.literal_eval(assignments[key])==[],key
assert ast.literal_eval(assignments['PHASES'])=={'pair7-preflight':(210,10),'pair7-delivery':(240,23),'pair7-engine-ci-binding':(180,5)}
ns=ast.get_source_segment(common_text,nf['StrictCommands'])
old_ns=ast.get_source_segment(old_text,of['StrictCommands'])
new_exclusions="        assert a['sourceReview']['path'] not in SELECTED and self.manifest_row['path'] not in SELECTED\n        assert all(value['path'] not in SELECTED for value in a['driverSources'])\n"
assert ns.count(new_exclusions)==1
assert ns.replace(new_exclusions,'').replace('accept-exact-android-pair7-delivery-source-and-argv','accept-exact-axis-pair7-delivery-source-and-argv')==old_ns
check=ast.get_source_segment(common_text,nf['check_sources'])
check=check.replace("    if PUBLIC_CONTROL_OUTPUTS_DECISION_ROW is not None:\n        assert row(ROOT / PUBLIC_CONTROL_OUTPUTS_DECISION_ROW['path']) == PUBLIC_CONTROL_OUTPUTS_DECISION_ROW","    assert row(ROOT / PUBLIC_CONTROL_OUTPUTS_DECISION_ROW['path']) == PUBLIC_CONTROL_OUTPUTS_DECISION_ROW")
check=check.replace("    if FORMATTING_DECISION_ROW is not None:\n        assert row(ROOT / FORMATTING_DECISION_ROW['path']) == FORMATTING_DECISION_ROW","    assert row(ROOT / FORMATTING_DECISION_ROW['path']) == FORMATTING_DECISION_ROW")
check=check.replace("assert history['closedCommandSeries']['total'] == 109","assert history['closedCommandSeries']['total'] == 71")
check=check.replace("\n    assert S['ordinaryHost']['workflowID'] == 393488255",'')
assert check==ast.get_source_segment(old_text,of['check_sources'])
source_rows.insert(0,identity(OUT/'selection_common_android_pair7.py.template'))
argv_rows={}
for phase,count,seconds,oldtemplate in [
 ('pair7-preflight',10,210,'argv-canonical-preflight.template.json'),
 ('pair7-delivery',23,240,'correction-2/argv-canonical-delivery.template.json'),
 ('pair7-engine-ci-binding',5,180,'argv-canonical-engine-ci-binding.template.json')]:
    path=OUT/('argv-'+phase+'.template.json')
    manifest=data(path)
    assert manifest['phase']==phase and manifest['session']=={'seconds':seconds,'count':count,'prefix':phase+'-'}
    assert manifest['schema']==1 and manifest['selection'] is None and manifest['manualWorkflowDispatchLimit']==0
    assert manifest['expectedEngineWorkflowID']==393488255 and manifest['preparationOnly'] is True
    assert len(manifest['commands'])==len({r['name'] for r in manifest['commands']})==count
    prior=data(OLD/oldtemplate)['commands']
    expected=[]
    for row in prior:
        updated=dict(row)
        for key in ('argv','effectiveArgv'):
            updated[key]=[normalized(token.replace(str(OLD),str(OUT))).replace('2c751cbbc300efc9aa766b5d4add648610ca0341','3da0d01bd05565a6aad905997beddf6805826241') for token in row[key]]
        expected.append(updated)
    assert manifest['commands']==expected,phase
    for row in manifest['commands']:
        argv=row['argv']
        assert all(type(t) is str and t and '\0' not in t for t in argv)
        effective=['git','-c','gc.auto=0','-c','maintenance.auto=false',*argv[1:]] if argv[0]=='git' else argv
        assert row['effectiveArgv']==effective
        assert row['kind']==('mutation' if row['name'] in ('stage','commit','push') else 'read')
        assert argv[:2]!=['gh','workflow']
    argv_rows[phase]=identity(path)
delivery=data(OUT/'argv-pair7-delivery.template.json')['commands']
assert next(r for r in delivery if r['name']=='committed-head')['argv'][-1]=='HEAD^@'
assert next(r for r in delivery if r['name']=='index-selected')['argv'][-1]=='{SELECTED_PATHS_EXPAND_HERE}'
assert next(r for r in delivery if r['name']=='authored-check')['argv'][-1]=='{FORMATTING_PATHS_EXPAND_HERE}'
assert next(r for r in delivery if r['name']=='push')['argv'][-1]=='{COMMITTED_SHA}:refs/heads/main'
selection=data(OUT/'selection.template.json')
assert selection['formattingExclusions']==[] and selection['exactPublicControlOutputRows']==[]
assert selection['exceptionRootDecisions']=={'formatting':None,'publicControlOutputs':None}
assert selection['ordinaryHost']['workflowID']==393488255
assert selection['selectedRows'] is selection['commitMessage'] is None
assert selection['runtimeMaterializedSourcesArgvAuthorityCurrentRecordsAndFinalReviewExcluded'] is True
authority=data(OUT/'authority.template.json')
assert authority['authorized'] is False and authority['selection'] is None
assert authority['stageLimit'] is authority['commitLimit'] is authority['nonforcePushLimit'] is None
assert authority['manualWorkflowDispatchLimit']==0 and authority['oldDriverReplayAllowed'] is False
assert "(FORMATTING_DECISION_ROW is None) == (not FORMATTING_EXCLUSIONS)" in common_text
assert "(PUBLIC_CONTROL_OUTPUTS_DECISION_ROW is None) == (not PUBLIC_CONTROL_OUTPUTS)" in common_text
assert "('raw', 'local', 'state', 'streams', 'extract', 'extracted', 'commands')" in common_text
assert "parts[-1] != 'authority.json' and not parts[-1].startswith('authority-snapshot-')" in common_text
assert "assert not SELECTED.intersection" in common_text
assert "self.check_bindings(); check_sources()" in common_text
assert "'accept-exact-android-pair7-delivery-source-and-argv'" in common_text
assert read(OUT/'.gitignore')==b'*\n'
summary={
 'status':'PASS_INERT_PAIR7_PREPARATION_SOURCE_DATA_ONLY',
 'preparation':prep_row,'inventory':inventory,'driverTemplates':source_rows,'argvTemplates':argv_rows,
 'helper':identity(OUT/'owned.py'),'helperOnlyChanges':'Two equal-length 40-byte baseline literals on line111; reverse repin reproduces every prior byte.',
 'previousActualSeal':identity(OLD/'review/actual/seal.json'),
 'historicalClosedCommands':109,'historicalExitZero':108,'historicalClosedStageExitOne':1,
 'baseline':history['baseline'],'phaseCounts':[10,23,5],
 'allFourExactUnconditionalFirstRefusalsAndASTChecks':True,'subjectOrHelperSourceExecutedOrImported':False,
 'priorFiveFormattingAndTenPublicOutputRowsCarried':0,'initialFormattingExceptions':0,'initialPublicOutputExceptions':0,
 'optionalExceptionsRequireNewExactRootDecisionAndIdentityRowsBeforeEveryCommand':True,
 'newRuntimeAndFinalSourceReviewSelectionExclusions':True,'newRawExtractLogAuthorityBans':True,
 'finiteFullSelectedIndexNULRawParentAndNonforcePushProofsPreserved':True,
 'HEADAllParentsExactSoleParentProofRetained':True,'ordinaryWorkflowID':393488255,'manualWorkflowPhases':0,
 'finalSelectionAndMaterializedSourceReviewPending':True,'actualAuthorityGranted':False,'actualCommandsExecuted':0,
 'checkerPython':sys.version,'checkerInterpreter':sys.executable,'readBytes':TOTAL,'maxFileReadBytes':200000,'aggregateReadBoundBytes':2000000}
print(json.dumps(summary,indent=2))

