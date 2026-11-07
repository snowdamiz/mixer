"""Record actual delivery/status and release globals; no further remote mutation."""
import json
from owned import OUT,ROOT,now,row,save
d=json.loads((OUT/'dispatch-receipt.json').read_bytes());ci=json.loads((OUT/'initial-ci.json').read_bytes())
experiment=next(r for r in ci['headRuns'] if r['id']==d['run']['id'])
engine=next(r for r in ci['headRuns'] if r['path']=='.github/workflows/verify.yml')
summary={'schema':1,'at':now(),'commit':d['head'],'tree':d['tree'],'profile':d['inputs']['profile'],
    'dispatchCallsMade':1,'run':experiment,'engineRun':engine,'runtimeArtifactReview':'pending',
    'fullOriginalObservationGeometryAndConsumingCleanup':'not inferred from workflow success',
    'retryOrFallbackAuthorized':False,'productionDefaultOrGA':False}
save('workflow-status-summary.json',summary)
for name in ('PLAN.md','STATUS.md'):
    p=ROOT/name;t=p.read_text();old='One manual dispatch is authorized after this delivery.'
    new=f"The sole manual dispatch at `{d['head'][:8]}` is [run {experiment['id']}]({experiment['html_url']}); its workflow completed successfully, as did ordinary Engine [run {engine['id']}]({engine['html_url']}). The experiment artifact has not yet been reviewed, so full original observations, compiled geometry and consuming cleanup are not inferred from the green workflow."
    assert t.count(old)==1;t=t.replace(old,new)
    t=t.replace('Fresh compilation, twelve finite controls, the original harness and conservative geometry must admit the sole full attempt; actual execution remains pending.', 'Fresh compilation, twelve finite controls, the original harness and conservative geometry remain required admission; their actual receipts and the full runtime result await artifact review.')
    p.write_text(t)
def update(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key in ('currentDense512CompletionSelection','dense512CompletionSelection'):
                item.update({'deliveryStatus':'pushed nonforce; sole selected dispatch completed workflow success; artifact review pending',
                    'commit':d['head'],'tree':d['tree'],'dispatchCallsMade':1,'run':experiment,
                    'actualCompilationFiniteHarnessGeometryAndFullRun':'artifact review pending; workflow success alone is not acceptance',
                    'workflowStatusSummary':row(OUT/'workflow-status-summary.json')})
            else:update(item)
    elif isinstance(value,list):
        for item in value:update(item)
for name in ('work-graph.json','gates/ga.json'):
    p=ROOT/name;value=json.loads(p.read_bytes());update(value)
    if name=='work-graph.json':value['updated']=now()
    else:assert [sum(x['status']==s for x in value['gates']) for s in ('running','planned','verified')]==[8,30,0]
    p.write_text(json.dumps(value,indent=2)+'\n')
commands=[]
for path in sorted(OUT.glob('*.command.json')):
    r=json.loads(path.read_bytes())
    assert all(r[k] is True for k in ('admitted','directChildReaped','ownedGroupAbsent','stdoutEOF','stderrEOF'))
    assert r['exit']==0 and not r['timedOut'] and r['failure'] is None
    admission=json.loads(path.with_name(path.name.replace('.command.json','.admission.json')).read_bytes())
    assert admission['identity']==r['identity']=={'pid':r['ownedPID'],'pgid':r['ownedPID'],'sid':r['ownedPID']}
    commands.append({'receipt':row(path),'admission':row(path.with_name(path.name.replace('.command.json','.admission.json')))})
pre=json.loads((OUT/'preflight.json').read_bytes())
for path,h in pre['protectedFiles'].items():assert row(ROOT/path)['sha256']==h
r=json.loads((OUT/'receipt.json').read_bytes())
save('handoff.json',{'schema':1,'at':now(),'head':d['head'],'tree':d['tree'],'pushed':True,'force':False,
    'dispatchCallsMade':1,'profile':d['inputs']['profile'],'run':experiment,'engineRun':engine,
    'selectedFiles':r['selectedFilesIncludingManifest'],'selectedBytes':r['selectedBytesIncludingManifest'],
    'trackedSparseDependencyMembers':121,'localGitGhCommands':len(commands),'commands':commands,
    'allLocalGitGhCommandsAdmittedReapedGroupsAbsentEOF':True,'protectedFilesPreserved':True,'wranglerUntouched':True,
    'firstPreflightFailureRetained':row(OUT/'first-preflight-failure.json'),
    'globalOwnershipReleased':True,'globalsAfterDispatchUncommitted':[row(ROOT/p) for p in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json')],
    'next':'Read-only artifact acquisition and independent actual semantic/custody review; no dispatch retry authorized',
    'rawCIPublished':False,'signedArtifactURLsPrintedOrSaved':False,'compilerRuntimeNativeUICaptureProcessInventoryOrHeldProbeStarted':False,
    'gateCounts':{'running':8,'planned':30,'verified':0},'productionOrGA':False})
print(json.dumps({'head':d['head'],'tree':d['tree'],'run':experiment,'engine':engine,'gitGhCommands':len(commands),'allAdmittedReapedGroupsAbsentEOF':True,'globalsReleased':True,'artifactReview':'pending'}))
