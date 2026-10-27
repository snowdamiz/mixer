"""Compile checked constant recipes; never integrate a runtime admission route."""
import json,shutil
from collections import defaultdict
from probe import ROOT,INPUT,save,run
d=json.loads((ROOT/'inventory.json').read_text());groups={c:defaultdict(int) for c in d['formulas']}
for r in d['roles']:
 for c,n in r['funding'].items():groups[c][r['template']]+=n
groups['selected-unconditional']['accepted-encoder-pregrant']=d['encoder_join']['unconditional_bytes']
groups['admitted-only']['accepted-encoder-admitted']=d['encoder_join']['admitted_only_bytes']
names={'common-extra':'COMMON_EXTRA','selected-unconditional':'SELECTED_UNCONDITIONAL','admitted-only':'ADMITTED_ONLY'}
code='// Generated only from exact role inventory.json. Const-only review artifact.\n// No runtime functions, arrays, admission integration, or operational selection.\n'
for category,values in groups.items():
 code+='pub const '+names[category]+':u64=0u64\n'
 for key,n in values.items():
  if n:code+=' // '+key+'\n .checked_add('+str(n)+').expect("checked source-role sum")\n'
 code+=';\n'
code+='pub const HOST_CALLER:u64='+str(d['host_caller_bytes'])+';\n'
code+='pub const SELECTED_FROM_LEGACY:u64=COMMON_EXTRA.checked_add(SELECTED_UNCONDITIONAL).expect("selected sum");\n'
code+='pub const ADMITTED_FROM_LEGACY:u64=SELECTED_FROM_LEGACY.checked_add(ADMITTED_ONLY).expect("phase sum");\n'
code+='pub const HOST_ADMITTED_FROM_LEGACY:u64=ADMITTED_FROM_LEGACY.checked_add(HOST_CALLER).expect("host sum");\n'
code+='const _:()=assert!(COMMON_EXTRA==77144 && SELECTED_UNCONDITIONAL==941467 && ADMITTED_ONLY==430175 && HOST_CALLER==81327 && HOST_ADMITTED_FROM_LEGACY==1530113);\n'
(ROOT/'checked-recipe-constants.rs').write_text(code)
for unit in (False,True):
 label='checked-constant-recipe-'+('unit' if unit else 'production');vm=ROOT/('owned-work/'+label+'/vm');assert not vm.exists();shutil.copytree(INPUT/'source/vm',vm)
 seam='\nmod owned_const_recipe_control {\n'+code+'\n}\n';p=vm/'src/experimental_swift_reactor/cache/initial_profile_v1.rs';p.write_text(p.read_text()+seam)
 rc=run(label,['--emit=metadata','-o',str(ROOT/('owned-work/'+label+'.rmeta'))],vm=vm,unit=unit)
 assert rc==0;shutil.rmtree(vm.parent)
label='checked-constant-recipe-overflow-negative';vm=ROOT/('owned-work/'+label+'/vm');assert not vm.exists();shutil.copytree(INPUT/'source/vm',vm)
seam='\nmod owned_const_recipe_overflow_control {\n'+code+'\nconst _:u64=u64::MAX.checked_add(COMMON_EXTRA).expect("required overflow refusal");\n}\n';(ROOT/'overflow-negative-seam.rs').write_text(seam)
p=vm/'src/experimental_swift_reactor/cache/initial_profile_v1.rs';p.write_text(p.read_text()+seam)
rc=run(label,['--emit=metadata','-o',str(ROOT/'owned-work/overflow-negative.rmeta')],vm=vm)
assert rc!=0;err=(ROOT/'commands'/label/'stderr').read_text();assert 'E0080' in err and 'required overflow refusal' in err;shutil.rmtree(vm.parent)
save(ROOT/'recipe-control-results.json',{'positive_contexts':['production','cfg(test)'],'overflow_negative':'E0080 at checked u64 fold','source_artifact':'checked-recipe-constants.rs','integration':'Const-only isolated recipe artifact; current frozen144 source, original budget limits, placeholder functions, WorkAuditPending and actual writer route untouched','runtime_invocations':0})
