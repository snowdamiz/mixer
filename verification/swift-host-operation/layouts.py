#!/usr/bin/env python3
from pathlib import Path
import json,sys,shutil
import collect as c
import metadata

def verify_fields(layout,schema,unit):
 expected={r['field']for r in schema if unit or r['config']!='unit'};assert set(layout['fields'])==expected
 end={}
 for r in sorted((r for r in schema if r['field']in expected),key=lambda r:(r['ownerClass'],layout['fields'][r['field']]['offset'])):
  v=layout['fields'][r['field']];cls=r['ownerClass'];assert v['offset']>=end.get(cls,0);assert v['offset']%v['alignment']==0;end[cls]=v['offset']+v['bytes'];assert end[cls]<=layout['classes'][cls]['bytes']
def main(prefix):
 c.SCRATCH=c.scratch();schema=json.loads((c.HERE/'inventory-schema.json').read_text());records=[]
 for label in ['baseline','candidate']:
  vm=metadata.setup(label,schema)
  archived=prefix+'-metadata-'+label;c.archive(archived,vm)
  for features,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
   for profile in ['debug','release']:
    for unit in [False,True]:
     config='unit'if unit else'production';name='-'.join([prefix,label,features,profile,config]);t=c.target(vm,features,profile,prefix+'-layout-'+config);env={'CARGO_TARGET_DIR':str(t)};release=['--release']if profile=='release'else[]
     args=['cargo',*(['test','--lib','--no-run']if unit else['build','--bin','host_contract_layout']),'--offline','--locked',*flags,*release,'--message-format=json-render-diagnostics']
     p,_=c.command('build-'+name,args,vm,env)
     rows=[json.loads(l)for l in p.stdout.decode().splitlines()if l.startswith('{')]
     artifacts=[x for x in rows if x.get('reason')=='compiler-artifact'and x.get('executable')and ((unit and x['profile']['test']and x['target']['name']=='mixer_vm'and x['target']['src_path'].endswith('/src/lib.rs'))or(not unit and x['target']['name']=='host_contract_layout'))]
     assert len(artifacts)==1 and artifacts[0]['fresh']is False
     a=artifacts[0];args=['--exact','experimental_swift_reactor::execution::frame_operations::host_contract_layout_only','--nocapture','--test-threads=1']if unit else[]
     output,record=c.retain_and_run(name,a,vm,env,args=args);layout=metadata.parse(output.stdout.decode());record.update(label=label,features=features,profile=profile,unit=unit,layout=layout)
     assert layout['totals']['ticket_max']==86 and layout['totals']['state_limit']==134217728 and layout['totals']['combined_limit']==268435456
     if label=='candidate':
      baseline=next(x['layout']for x in records if(x['label'],x['features'],x['profile'],x['unit'])==('baseline',features,profile,unit))
      assert layout['types']==baseline['types']and layout['owners']==baseline['owners'];verify_fields(layout,schema,unit)
      for k,v in baseline['totals'].items():
       expected=v+(layout['classes']['HostPermanentPositions']['bytes'] if k=='header' else layout['classes']['HostActivePositions']['bytes'] if k=='frame' else 0)
       assert layout['totals'][k]==expected,(k,expected,layout['totals'][k])
     records.append(record);c.save(prefix+'-layouts.json',records)
 c.save(prefix+'-layout-summary.json',dict(contexts=len(records),positiveFields=len(schema),allOriginalOwnersEqual=True,allPriorComponentTotalsEqual=True,headerAndFrameCheckedAsExactAdditions=True,distinctEmptyTargets=len({x['cargoTarget']for x in records})==len(records),hostBehaviorExecuted=False))
 print('Fresh paired layouts complete',len(records),flush=True)
if __name__=='__main__':main(sys.argv[1])
