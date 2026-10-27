"""Fresh compiler negatives; no admitted runtime/writer execution."""
from pathlib import Path
import shutil,json,re,importlib.util,sys,hashlib
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('composition_compile',ROOT/'compile_source.py')
compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
SOURCE=ROOT/'source/vm'
CASES={
 'ordinary-body-ingress':('src/experimental_swift_reactor/cache.rs',None,'''\nfn negative_ordinary_body_snapshot_v1(body:super::retained_profile_loader_v1::AdoptionBodyV1,budget:SwiftRunBudget,started:std::time::Instant,cancellation:crate::Cancellation){
 let _=RuntimeControl::adopt_snapshot_body_v1(body,budget,started,cancellation);
}\n''',['E0308']),
 'forge-selected-capability':('src/experimental_swift_reactor/cache.rs',None,'''\nfn negative_forge_selected_body_v1(body:super::retained_profile_loader_v1::AdoptionBodyV1){
 let _=super::retained_profile_loader_v1::SelectedSnapshotBodyV1(body);
}\n''',['E0603']),
 'extract-owned-control':('src/experimental_swift_reactor/cache.rs',None,'''\nfn negative_extract_scope_control_v1(scope:super::control::SnapshotScopeV1){let _=scope.control;}\n''',['E0616']),
 'direct-earlier-control':('src/experimental_swift_reactor/cache/initial_profile_v1.rs','control:access.shared_control()','control',['E0502']),
 'mutate-through-guard':('src/experimental_swift_reactor/cache/initial_profile_v1.rs',None,'''\nfn negative_mutate_guard_v1(initial:&InitialProfileBorrowV1<'_>){let _=initial.control.snapshot_debit_v1(1);}\n''',['E0596']),
 'extend-closed-branch':('src/experimental_swift_reactor/cache.rs',None,'''\nstruct NegativeStrategyV1;
impl initial_profile_v1::branch_seal_v1::Closed for NegativeStrategyV1 {}\n''',['E0603']),
}
results=[]
tag=sys.argv[1] if len(sys.argv)>1 else ''
for mode in ['debug','optimized']:
 for name,(relative,old,new,expected) in CASES.items():
  label='negative-'+(tag+'-' if tag else '')+mode+'-'+name
  destination=ROOT/'owned-work'/label/'vm'
  assert not destination.exists();shutil.copytree(SOURCE,destination)
  target=destination/relative;text=target.read_text()
  if old is None:text+=new
  else:
   assert text.count(old)==1;text=text.replace(old,new,1)
  target.write_text(text)
  compiler.VM=destination
  code=compiler.run(label,unit=False,opt=mode=='optimized',emit='metadata',expected=1)
  stderr=(ROOT/'commands'/label/'stderr').read_text()
  actual=sorted(set(re.findall(r'error\[(E\d+)\]',stderr)))
  passed=code==1 and actual==expected
  result={'name':name,'mode':mode,'relative_source':relative,'replacement_from':old,'replacement_to':new,'expected_diagnostics':expected,'actual_diagnostics':actual,'passed':passed,'scope':'compiler privacy/ownership test only'}
  results.append(result)
  shutil.rmtree(destination.parent)
  assert passed,result
(ROOT/('negative-results-'+tag+'.json' if tag else 'negative-results.json')).write_text(json.dumps({'schema':1,'tag':tag,'results':results,'all_passed':all(x['passed'] for x in results)},indent=2)+'\n')
