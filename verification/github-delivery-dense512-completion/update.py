"""Reconcile only the selected source delivery; runtime evidence stays pending."""
import copy, json
from owned import OUT, ROOT, now, row, save
before=[row(ROOT/f) for f in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json')]
old='Independent review passes 46 offline methods. Root [selects one completion run](verification/github-delivery-dense512-completion/selection.json), after fresh compilation, twelve finite controls, the original harness and geometry admission. Actual execution remains pending.'
new='The producer passes 23 source checks and 36 pure methods; independent review passes 46 methods including 36 replayed methods. Root [selects one completion run](verification/github-delivery-dense512-completion/selection.json). The exact reviewed workflow is installed, and all 121 existing sparse dependency files match their tracked blobs and frozen bindings. One manual dispatch is authorized after this delivery. Fresh compilation, twelve finite controls, the original harness and conservative geometry must admit the sole full attempt; actual execution remains pending.'
for name in ('PLAN.md','STATUS.md'):
    p=ROOT/name;t=p.read_text();assert t.count(old)==1;p.write_text(t.replace(old,new))
w=json.loads((ROOT/'work-graph.json').read_bytes());g=json.loads((ROOT/'gates/ga.json').read_bytes())
def update(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key in ('currentDense512CompletionSelection','dense512CompletionSelection'):
                assert item['profile']=='dense512-completion-v1'
                item.update({'workflow':row(ROOT/'.github/workflows/swift-dense512-completion.yml'),
                    'producerSourceChecks':23,'producerPureMethods':36,'independentMethods':46,'independentReplayMethods':36,
                    'deliveryPreflight':row(OUT/'preflight.json'),'trackedSparseDependenciesVerified':121,
                    'deliveryStatus':'exact workflow installed; one selected push and manual dispatch pending',
                    'retryOrFallbackSelected':False})
            else:update(item)
    elif isinstance(value,list):
        for item in value:update(item)
update(w);update(g);w['updated']=now()
assert [sum(x['status']==s for x in g['gates']) for s in ('running','planned','verified')]==[8,30,0]
for name,d in (('work-graph.json',w),('gates/ga.json',g)):(ROOT/name).write_text(json.dumps(d,indent=2)+'\n')
save('metadata-validation.json',{'schema':1,'at':now(),'before':before,'after':[row(ROOT/f) for f in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json')],'gateCounts':{'running':8,'planned':30,'verified':0},'compilerRuntimeNativeUICaptureOrHeldProbeStarted':False})
