"""Finite law tests and hostile controls for the resource interface candidate."""
import copy,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from model import Refused,U64,add,mul,plain_vector,byte_box,source_ceiling_cuts,components,evaluate_row
from internal_graph import Graph
D=Path(__file__).resolve().parent
contract=json.loads((D/'contract.json').read_text());binding=contract['binding']
rows=json.loads((D/'rows.json').read_text());cuts=source_ceiling_cuts(contract,binding,'closed-file-os-or-static-message')
checks=0;groups={}
def check(name,ok):
    global checks
    if not ok:raise AssertionError(name)
    checks+=1;groups[name.split(':')[0]]=groups.get(name.split(':')[0],0)+1
def refused(name,fn,errors=(Refused,)):
    try:fn()
    except errors:check(name,True)
    else:raise AssertionError('accepted-hostile:'+name)

check('concrete:File',cuts['File']=={'interface_work':9,'native_resource_backing':73})
check('concrete:Arc',cuts['Arc<AtomicBool>']=={'interface_work':15,'native_resource_backing':173})
check('concrete:Error',cuts['Error']=={'interface_work':3,'native_resource_backing':32})
check('concrete:returned',components(rows,cuts,['File','Option<File>','ReturnedLoaderFilesV1','SetupOutcomeV1','SelectedValidatedProfileV1','LoaderFailureV1','Cancellation'])['returned_payload']==45195489+6*(9+73)+(15+173)+(3+32))
for field in binding:
    bad=dict(binding);bad[field]='wrong'
    refused('identity:'+field,lambda:source_ceiling_cuts(contract,bad,'closed-file-os-or-static-message'))
bad=dict(binding);bad['extra']='inferred'
refused('identity:unknown-field',lambda:source_ceiling_cuts(contract,bad,'closed-file-os-or-static-message'))
for provenance in ('generic-Read','custom-Error','Error-new','arbitrary-positive-cut','unknown',None,True):
    refused('error-provenance:'+str(provenance),lambda:source_ceiling_cuts(contract,binding,provenance))
for name in contract['vectors']:
    for key in contract['vectors'][name]:
        bad=copy.deepcopy(contract);bad['vectors'][name][key]=0
        refused('contract-vector:'+name+key,lambda:source_ceiling_cuts(bad,binding,'closed-file-os-or-static-message'))
for name in contract['interfaces']:
    bad=copy.deepcopy(contract);bad['interfaces'][name]['records'].pop()
    refused('contract-interface:'+name,lambda:source_ceiling_cuts(bad,binding,'closed-file-os-or-static-message'))
bad=copy.deepcopy(contract);bad['interfaces']['Arc<AtomicBool>']['requested_backing_bytes']=8
refused('contract-interface:inline-handle-as-Arc-backing',lambda:source_ceiling_cuts(bad,binding,'closed-file-os-or-static-message'))

# Independent explicit enumeration of visited element fields and extents.
# For uniform non-ZST T, actual length<=capacity and requested B=capacity*E.
# The law also covers a conservative byte ceiling above actual requested B.
for nodes in (1,2,3,5,7,11,14,19):
    for extent in (1,4,12,16,20,32,40,56,136):
        for capacity in range(65):
            backing=capacity*extent
            for live in range(capacity+1):
                out=plain_vector({'max_requested_bytes':backing,'max_live_elements':live,'element_nodes':nodes})
                actual_source=4+sum(nodes for _ in range(live))
                actual_native=24+backing+sum(nodes*extent for _ in range(live))
                check('finite-element-law:source',out['interface_work']==actual_source)
                check('finite-element-law:native',out['native_resource_backing']>=actual_native)
                if live<capacity:
                    plus=plain_vector({'max_requested_bytes':backing,'max_live_elements':live+1,'element_nodes':nodes})
                    check('monotone-live:one',sum(plus.values())>=sum(out.values()))
for b in range(129):
    for live in (0,b//2,b):
        out=byte_box({'max_requested_bytes':b,'max_live_elements':live})
        check('finite-box-law:sum',sum(out.values())==3+live+24+2*b)
for n in (-1,True,False,None,1.5,U64+1,'1'):
    refused('u64:bad-add:'+str(n),lambda:add(n))
    refused('u64:bad-mul:'+str(n),lambda:mul(n,1))
refused('u64:add-overflow',lambda:add(U64,1))
refused('u64:mul-overflow',lambda:mul(U64,2))
refused('vector:live-above-bytes',lambda:plain_vector({'max_requested_bytes':0,'max_live_elements':1,'element_nodes':1}))
refused('vector:missing-bound',lambda:plain_vector({'max_requested_bytes':1,'element_nodes':1}))
refused('vector:overflow',lambda:plain_vector({'max_requested_bytes':U64,'max_live_elements':1,'element_nodes':2}))
refused('box:missing-bound',lambda:byte_box({'max_requested_bytes':1}))

dynamic=next(r for r in rows if r['type']=='SwiftFunctionCache')
for name in dynamic['resource_frontiers']:
    selected={k:copy.deepcopy(cuts[k]) for k in dynamic['resource_frontiers']};selected.pop(name)
    refused('missing-frontier:'+name,lambda:evaluate_row(dynamic,selected))
for name in ('Vec<Type>','Vec<DecodedInstruction>','Vec<u32>'):
    selected={k:copy.deepcopy(cuts[k]) for k in dynamic['resource_frontiers']};selected['Vec<SwiftSlot>']['element_cuts'].pop(name)
    refused('nested-slot-frontier:'+name,lambda:evaluate_row(dynamic,selected))
for value in (0,1,63,65,True,None):
    selected={k:copy.deepcopy(cuts[k]) for k in dynamic['resource_frontiers']};selected['Vec<SwiftSlot>']['max_live_elements']=value
    refused('slot-live:'+str(value),lambda:evaluate_row(dynamic,selected))
for value in (0,8,135,137,True):
    selected={k:copy.deepcopy(cuts[k]) for k in dynamic['resource_frontiers']};selected['Vec<SwiftSlot>']['element_inline_bytes']=value
    refused('slot-layout:'+str(value),lambda:evaluate_row(dynamic,selected))
for name in cuts:
    if name=='Vec<SwiftSlot>':continue
    r={'type':'hostile','inline_bytes':1,'structural_occurrence_allowance':1,'resource_frontiers':{name:1}}
    for key in ('interface_work','native_resource_backing'):
        bad=copy.deepcopy(cuts[name]);bad[key]=0
        refused('positive-cut:'+name+key,lambda:evaluate_row(r,{name:bad}))
for spelling in ('Unknown','Option<File,u8>','Result<File>','Vec<File,Error>','[File;8193]'):
    refused('closed-graph:'+spelling,lambda:Graph([]).walk(spelling),(ValueError,KeyError))
recursive={'name':'Recursive','kind':'struct','fields':['Recursive']}
refused('closed-graph:recursive-owner',lambda:Graph([recursive]).walk('Recursive'),(ValueError,))
check('borrow-does-not-destroy:unknown-referent',Graph([]).walk('&Unknown')=={'nodes':1,'resources':{}})
result={'schema':1,'checks':checks,'groups':groups,'all_passed':True,
    'finite_law_cases_are_synthetic':True,'synthetic_values_selected_as_resource_policy':False,
    'compiler_product_fixture_native_UI_capture_executed':False}
raw=json.dumps(result,indent=2,sort_keys=True)+'\n'
if '--check-only' in sys.argv:assert (D/'controls.json').read_text()==raw
else:(D/'controls.json').write_text(raw)
print(json.dumps({'checks':checks,'groups':len(groups),'status':'passed'},sort_keys=True))
