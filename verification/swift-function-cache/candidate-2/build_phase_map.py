#!/usr/bin/env python3
"""Bind authored named-value phase assignments to executed compiler layouts."""
from pathlib import Path
import hashlib,json,re,subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=ROOT/'vm/src/experimental_swift_reactor/cache.rs'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def key(s):return re.sub(r'\s+','',s)
logs=[HERE/f'preflight-root-tail-layout-{mode}-final.log' for mode in ['debug','release']]
observations=[]
for log in logs:
 s=log.read_text();assert re.search(r'test result: ok\. 1 passed; 0 failed;',s)
 layouts={key(t):{'type':t,'size':int(n),'align':int(a)} for t,n,a in re.findall(r'^layout (.*?) (\d+) (\d+)$',s,re.M)}
 fields={}
 for model,name,ty,n,a,o in re.findall(r'^model (\w+) (\w+) (.*?) (\d+) (\d+) (\d+)$',s,re.M):
  fields.setdefault(model,[]).append({'field':name,'type':ty,'size':int(n),'align':int(a),'offset':int(o)})
 observations.append((layouts,fields))
assert observations[0]==observations[1]
layouts,fields=observations[0]
slots=[('control2','RuntimeControl','PreflightGroupA'),('control3','RuntimeControl','PreflightGroupB'),('proof2','ValidatedSwiftReactor','PreflightSetupInventory'),('proof3','ValidatedSwiftReactor','PreflightOwnerInventory'),('adopted2','AdoptedProof','PreflightPrimitiveInventory'),('adopted3','AdoptedProof','PreflightEnlargeInventory')]
slots=[{'whole_slot':slot,'whole_type':whole,'whole_bytes':layouts[whole]['size'],'phase_type':model,'phase_bytes':layouts[model]['size'],'phase_align':layouts[model]['align']} for slot,whole,model in slots]
for row in slots:assert row['phase_bytes']<=row['whole_bytes']
assert layouts['RootLeafInventory']['size']<=layouts['RuntimeControl']['size']
assert layouts['CompletionBorrowInventory']['size']<=layouts['RuntimeControl']['size']
foundation=[(3,'ValidatedSwiftReactor'),(3,'RuntimeControl'),(3,'AdoptedProof'),(4,'SwiftRunFailure'),(4,'SwiftRunUsage'),(6,'ReservationTicket'),(6,'Option<WasiUsage>')]
assert sum(n*layouts[t]['size'] for n,t in foundation)==16504
src=SOURCE.read_text();sums={}
for suffix in ['cleanup_temporary','construction','operation']:
 function='compute_cache_'+suffix+'_bytes';body=src[src.index('const fn '+function):];body=body[:body.index('\n}')]
 rows=[]
 for match in re.finditer(r'\(\s*(\d+)\s*,\s*size_of::<',body):
  i=match.end();j=i;depth=1
  while depth:
   if body[j]=='<':depth+=1
   elif body[j]=='>':depth-=1
   j+=1
  ty=key(body[i:j-1]);n=int(match.group(1));shape=layouts[ty]
  rows.append({'type':ty,'count':n,'size':shape['size'],'align':shape['align'],'bytes':n*shape['size']})
 assert rows;sums[function]={'objects':rows,'bytes':sum(r['bytes']for r in rows)}
bounds=list(map(int,re.search(r'bounds cleanup=(\d+) header=(\d+) construction=(\d+) operation=(\d+) foundation=(\d+)',logs[0].read_text()).groups()))
assert bounds[0]==sums['compute_cache_cleanup_temporary_bytes']['bytes']
assert bounds[2]==sums['compute_cache_construction_bytes']['bytes']
assert bounds[3]==sums['compute_cache_operation_bytes']['bytes']
record={'schema':'mixer-cache-candidate2-whole-slot-phase-map-v1','scope':'authored named Rust values only; no compiler stack, opaque std/platform implementation, allocator overhead or RSS claim','source':str(SOURCE.relative_to(ROOT)),'source_sha256':digest(SOURCE),'tests_source_sha256':digest(ROOT/'vm/src/experimental_swift_reactor/cache_tests.rs'),'debug_release_identical':True,'logs':{str(p.relative_to(HERE)):digest(p)for p in logs},'tool':subprocess.check_output(['/opt/homebrew/opt/rustup/bin/rustc','-Vv'],text=True),'preflight_slots':slots,'layouts':layouts,'model_fields':fields,'component_checked_sums':sums,'observed_bounds':dict(zip(['cleanup','header','construction','operation','foundation'],bounds)),'foundation_counts':[{'count':n,'type':t,'size':layouts[t]['size']}for n,t in foundation]}
(HERE/'preflight-root-tail-map.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'source_sha256':record['source_sha256'],'phase_bytes':{r['whole_slot']:r['phase_bytes']for r in slots},'root_leaf':layouts['RootLeafInventory']['size'],'completion':layouts['CompletionBorrowInventory']['size'],'bounds':record['observed_bounds']}))
