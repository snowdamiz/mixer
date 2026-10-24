"""Sixteen compiler-only paired source overlays; no executable metadata probes."""
import collect as c
from pathlib import Path
import json,gzip,shutil,tempfile,subprocess

BASELINE=c.ROOT/'vm'
FORMULAS={
 'header':'crate::experimental_swift_reactor::execution::EXECUTION_HEADER_BYTES.unwrap()',
 'frame':'super::FRAME_OPERATION_BYTES.unwrap()',
 'growth_permanent':'PERMANENT_BYTES','growth_active':'ACTIVE_BYTES',
 'original_growth_permanent':'size_of::<PermanentPositions>()','original_growth_active':'size_of::<ActivePositions>()',
 'frame_frozen_permanent':'super::FROZEN_PERMANENT_BYTES','frame_frozen_active':'super::FROZEN_ACTIVE_BYTES',
 'ticket_max':'MAX_RESERVATION_TICKETS',
}
def main():
 session=json.loads((c.HERE/'layout-tool-session.json').read_text());tool=json.loads((c.HERE/'layout-driver-build.json').read_text())
 assert c.sha(Path(tool['binary']).read_bytes())==tool['sha256']
 records=[]
 for features in ['swift','all']:
  for profile in ['debug','release']:
   for unit in [False,True]:
    cfg=f'{features}-{profile}-'+('unit'if unit else'production')
    pair={}
    for label in ['baseline','candidate']:
     print(label,cfg,flush=True)
     scratch=Path(tempfile.mkdtemp(prefix='mixer-lifecycle-layout-overlay-'));tree=scratch/'crate';attempt=None
     try:
      if label=='baseline':
       tree.mkdir()
       for name,pin in json.loads((c.HERE/'baseline-manifest.json').read_bytes()).items():
        data=(BASELINE/name).read_bytes();assert c.sha(data)==pin,name
        target=tree/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
      else:shutil.copytree(c.HERE/'candidate',tree)
      original=c.manifest(tree)
      expressions=dict(FORMULAS)
      if label=='candidate':expressions.update(lifecycle_permanent='lifecycle::PERMANENT_BYTES',lifecycle_active='lifecycle::ACTIVE_BYTES')
      fields='\n'.join(f'    {name}: [u8; {expression}],'for name,expression in expressions.items())
      suffix=('\n// Metadata-only compiler layout projection. Never instantiated.\n#[allow(dead_code)]\nstruct LifecycleFormulaProbe {\n'+fields+'\n}\n').encode()
      source=tree/'src/experimental_swift_reactor/memory_growth_operations.rs';before=source.read_bytes();source.write_bytes(before+suffix)
      projection={'originalManifest':original,'originalClosure':c.sha(c.enc(original)),'source':'src/experimental_swift_reactor/memory_growth_operations.rs','prefixSHA256':c.sha(before),'appendedSHA256':c.sha(suffix),'probeManifest':c.manifest(tree),'noRuntimeRoot':True}
      output=scratch/'layouts.jsonl'
      flags=['--no-default-features']+(['--features','experimental-swift-reactor']if features=='swift'else['--all-features'])+(['--release']if profile=='release'else[])
      code,attempt,out,err=c.run(['cargo','rustc','--lib','--locked','--offline',*flags,'--','--emit=mir','-Zmir-include-spans=yes']+(['--test']if unit else[]),tree=tree,env_extra={'RUSTC_BOOTSTRAP':'1','RUSTC_WRAPPER':tool['binary'],'MIXER_LAYOUT_SYSROOT':session['sysroot'],'MIXER_LAYOUT_OUTPUT':str(output)},label='paired-layout-'+label+'-'+cfg)
      c.save(attempt/'source-projection.json',projection)
      raw=output.read_bytes();c.save(attempt/'exact-layouts.jsonl.gz',gzip.compress(raw,mtime=0));output.unlink()
      assert code==0
      declarations={r['path']:r for r in [json.loads(line)for line in raw.decode().splitlines()]if r['kind']=='declaration'}
      probe=next(v for k,v in declarations.items()if k.endswith('::LifecycleFormulaProbe'))['layout']
      variant=probe['variants'][0]
      assert variant['fieldNames']==list(expressions)
      totals={name:field['bytes']for name,field in zip(variant['fieldNames'],variant['fields'])}
      assert totals['ticket_max']==86
      selected={k:v for k,v in declarations.items()if not '::lifecycle::'in k and not k.endswith('::LifecycleFormulaProbe')}
      pair[label]={'attempt':str(attempt.relative_to(c.HERE)),'sourceClosure':projection['originalClosure'],'probeSourceClosure':c.sha(c.enc(projection['probeManifest'])),'querySHA256':c.sha(raw),'totals':totals,'owners':selected}
     finally:
      holders=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(scratch)],capture_output=True)
      assert holders.returncode==1 and not holders.stdout
      files=[p for p in scratch.rglob('*')if p.is_file()];cleanup={'scratch':str(scratch),'holderCheckEmpty':True,'filesRemoved':len(files),'logicalBytesRemoved':sum(p.stat().st_size for p in files)}
      shutil.rmtree(scratch);cleanup['removed']=not scratch.exists()
      if attempt:c.save(attempt/'overlay-cleanup.json',cleanup)
    a=pair['baseline'];b=pair['candidate'];assert set(a['owners'])<=set(b['owners'])
    comparisons={}
    for path,left in a['owners'].items():
     right=b['owners'][path]
     def layout_signature(value):
      value=value['layout'];return {'type':value['type'],'bytes':value['bytes'],'alignment':value['alignment'],'fields':[{k:v for k,v in field.items()if k!='identity'}for field in value['fields']],'variants':[{k:([{ik:iv for ik,iv in field.items()if ik!='identity'}for field in v]if k=='fields'else v)for k,v in variant.items()}for variant in value['variants']]}
     assert layout_signature(left)==layout_signature(right),path
     comparisons[path]={'actualUnchangedLayout':True,'baselineDefPathHash':left['defPathHash'],'candidateDefPathHash':right['defPathHash'],'bytes':left['layout']['bytes'],'alignment':left['layout']['alignment']}
    for key in ['original_growth_permanent','original_growth_active','frame_frozen_permanent','frame_frozen_active','ticket_max']:assert a['totals'][key]==b['totals'][key]
    assert b['totals']['growth_permanent']==a['totals']['growth_permanent']+b['totals']['lifecycle_permanent']
    assert b['totals']['growth_active']==a['totals']['growth_active']+b['totals']['lifecycle_active']
    assert b['totals']['header']==a['totals']['header']+b['totals']['lifecycle_permanent']
    assert b['totals']['frame']==a['totals']['frame']+b['totals']['lifecycle_active']
    records.append({'context':cfg,**pair,'comparisons':comparisons,'noRuntimeExecution':True})
    c.save(c.HERE/'paired-layouts.json',records)
 print('All sixteen paired compiler layouts recorded without test/VM execution',flush=True)
if __name__=='__main__':main()
