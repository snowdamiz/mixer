#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,shutil
OUT=Path(__file__).resolve().parent
DEST=OUT/'foundation-findings'
STAGE=OUT/'staging/verification/component'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(n,d):(DEST/n).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def main():
 DEST.mkdir(exist_ok=False);observations=[]
 env=json.loads((STAGE/'environment-attempt-1.json').read_text())
 for config in ['host','unit']:
  for mode in ['debug','optimized']:
   name=f'{config}-{mode}-layout';source=STAGE/'commands/attempt-1'/name
   target=DEST/'commands'/name;target.mkdir(parents=True)
   for n in ['stdout','stderr','receipt.json']:(target/n).write_bytes((source/n).read_bytes())
   values=next(line[line.index('VALUES '):] for line in (source/'stdout').read_text().splitlines() if 'VALUES cleanup=' in line)
   actual={k:int(v) for k,v in (s.split('=') for s in values.split()[1:])}
   foundation=269080 if config=='host' else 269616;assert actual['foundation']==foundation and actual['construction']==61880
   observations.append({'configuration':config,'mode':mode,'VALUES':actual,'stdout_sha256':sha((source/'stdout').read_bytes()),'command_receipt_sha256':sha((source/'receipt.json').read_bytes()),'executable':env[f'{config}_{mode}_executable'],'foundation_plus_original_prepare_extra_source_derived':foundation+61880,'fresh_direct_prepared_ticket_sample':False})
 (DEST/'fresh-replay-environment.json').write_bytes((STAGE/'environment-attempt-1.json').read_bytes())
 witnesses=[]
 for path,start,end in [('src/experimental_swift_reactor/control.rs',505,553),('src/experimental_swift_reactor/cache.rs',1422,1455),('src/experimental_swift_reactor/cache.rs',1896,1908),('src/experimental_swift_reactor/execution.rs',847,896),('src/experimental_swift_reactor/execution.rs',2968,2995)]:
  b=(STAGE/'source/vm'/path).read_bytes();excerpt=''.join(b.decode().splitlines(keepends=True)[start-1:end]);witnesses.append({'path':path,'source_sha256':sha(b),'start_line':start,'end_line':end,'excerpt':excerpt,'excerpt_sha256':sha(excerpt.encode())})
 write('original-source-witnesses.json',{'schema':1,'witnesses':witnesses,'source_scope':'Original formula and phase/type sources remain unchanged from frozen baseline; aggregate536 delta is observed, not attributed solely to one named original subinventory'})
 for n in ['accounting.json','ACCOUNTING.md','decision.json']:(DEST/('candidate-'+n)).write_bytes((OUT/'candidate-evidence'/n).read_bytes())
 write('finding.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'Configuration-specific accounting receipt correction, no product source/limit insufficiency observed','candidate_seal_sha256':'50d1c32174ee4cbcade6095039261ea0ff8eed05680322bfb59b5de0dd4cd8b1','candidate_source_tree_sha256':'71a00fde8a43aef5a7e6104932d3f0ca10a5989fb686c99828937b05aa363c7c','observations':observations,'erroneous_candidate_fields':{'accounting.json.unchanged_foundation':269616,'accounting.json.headroom.production':71736,'decision.json.unchanged_foundation_bytes':269616,'ACCOUNTING.md':'Both configurations compared to269616; production headroom71736; blanket foundation wording requires configuration scope'},'corrected_values':{'production':{'source_union':197880,'observed_unchanged_foundation':269080,'headroom':71200,'prepare_enlarged_construction_source_derived':330960},'unit':{'source_union':197928,'observed_unchanged_foundation':269616,'headroom':71688,'prepare_enlarged_construction_source_derived':331496,'actual_fault_cleanup_quarantine':331496,'quarantine_tickets':1}},'scope':'Four fresh exact-source layout method observations plus original formula/prepare/complete source; source-derived sum is distinguished from directly sampled prepared ticket; source object union review continues','no_cap_deadline_formula_or_product_change_required':True,'root_addendum_needed_before_accounting_acceptance':True,'unit_quarantine_331496_remains_correct':True,'healthy_cleanup_zero_separate':True,'candidate_currently_accepted':False})
 members=[]
 for p in sorted(DEST.rglob('*')):
  if p.is_file():b=p.read_bytes();members.append({'path':str(p.relative_to(DEST)),'bytes':len(b),'sha256':sha(b)})
 write('seal.json',{'schema':1,'scope':'Immutable independent configuration-specific foundation finding','member_count':len(members),'total_bytes':sum(m['bytes'] for m in members),'members':members,'excluded':['seal.json','seal.sha256']})
 h=sha((DEST/'seal.json').read_bytes());(DEST/'seal.sha256').write_text(h+'  seal.json\n');print(f'FOUNDATION FINDING frozen {len(members)} members seal {h}')
if __name__=='__main__':main()
