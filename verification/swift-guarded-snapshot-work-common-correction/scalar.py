"""Standalone checked floor constants and integer boundaries; no Mixer runtime."""
import gzip
import json
import shutil
import sys
sys.dont_write_bytecode=True
from prepare import HERE,CONTROL,sha
from run import RUSTC,bounded

def main():
    assert not (HERE/'seal.json').exists()
    src=(HERE/'overlay'/CONTROL).read_text()
    recipe=src[src.index('const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1:'):src.index('/// Common named-source foundation:')]
    bases=[None,0,366312,366896]
    maximum=(1<<64)-1
    for subtotal in [78240,78240+1436,78240+1436+941467,78240+1436+941467+81327,78240+1436+941467+430175]:
        bases.extend([maximum-subtotal-1,maximum-subtotal,maximum-subtotal+1])
    bases=list(dict.fromkeys(bases))
    modules=[]
    for i,base in enumerate(bases):
        literal='None' if base is None else 'Some('+str(base)+')'
        modules.append('mod recipe_'+str(i)+' {\nconst FOUNDATION_CONSTRUCTION_BYTES:Option<usize>='+literal+';\n'+recipe+'''
pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}\n''')
    source='// Exact corrected const recipe with separately declared synthetic F0 inputs.\n'+'\n'.join(modules)
    source+='fn main(){let mut checks=0usize;\n'+''.join('checks+=recipe_'+str(i)+'::check();\n' for i in range(len(bases)))+'''
for bits in [32u32,64] {
 let limit=(1u128<<bits)-1;
 for host in [0u128,81_327] {
  for delta in [78_240u128,78_240+1_436,78_240+1_436+941_467,78_240+1_436+941_467+host,78_240+1_436+941_467+host+430_175] {
   for base in [0u128,366_312,366_896,limit-delta-1,limit-delta,limit-delta+1,limit] {
    let mut actual=Some(base);
    for term in [78_240u128,1_436,941_467,host,430_175] {actual=actual.and_then(|n|n.checked_add(term)).filter(|n|*n<=limit);}
    let wide=base+78_240+1_436+941_467+host+430_175;
    assert_eq!(actual,if wide<=limit{Some(wide)}else{None});checks+=1;
   }
  }
 }
}
assert!(usize::MAX.checked_add(1_436).is_none());checks+=1;
assert!(u64::MAX.checked_add(1_272).is_none());checks+=1;
println!("{} checked common/selected/admitted floor and overflow controls passed; standalone integers; cfg_test={}",checks,cfg!(test));
}
'''
    for mode in ['production','unit']:
        label='scalar-'+mode
        folder=HERE/'commands'/label;folder.mkdir(parents=True,exist_ok=False)
        scratch=HERE/'owned-work'/label;scratch.mkdir(parents=True,exist_ok=False)
        (folder/'scalar-source.rs').write_text(source);(scratch/'scalar.rs').write_text(source)
        env={'PATH':'/usr/bin:/bin','TMPDIR':str(scratch)}
        version,versionerr,vr=bounded([str(RUSTC),'--version','--verbose'],env,HERE,10)
        (folder/'compiler-version-stdout').write_bytes(version);(folder/'compiler-version-stderr').write_bytes(versionerr)
        try:
            argv=[str(RUSTC),'--crate-name','common_work_floor','--edition=2021','-C','overflow-checks=yes']
            if mode=='unit':argv+=['--cfg','test']
            argv+=[str(scratch/'scalar.rs'),'-o',str(scratch/'scalar')]
            out,err,receipt=bounded(argv,env,HERE,30)
            (folder/'stdout.gz').write_bytes(gzip.compress(out,mtime=0));(folder/'stderr').write_bytes(err)
            receipt.update(schema=1,environment=env,compiler_sha256=sha(RUSTC.read_bytes()),compiler_version=version.decode(),
                compiler_version_command=vr,source_sha256=sha(source.encode()),exact_recipe_sha256=sha(recipe.encode()),
                stdout_sha256=sha(out),stderr_sha256=sha(err),scope='standalone exact const recipe with synthetic F0 inputs; actual floors checked separately')
            (folder/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
            assert receipt['exit_code']==0 and receipt['owned_group_absent'] and not receipt['timed_out'],err.decode()
            out,err,receipt=bounded([str(scratch/'scalar')],env,scratch,10)
            (folder/'test-stdout').write_bytes(out);(folder/'test-stderr').write_bytes(err)
            receipt.update(schema=1,environment=env,source_sha256=sha(source.encode()),executable_sha256=sha((scratch/'scalar').read_bytes()),
                stdout_sha256=sha(out),stderr_sha256=sha(err),scope='standalone checked integers only; no Mixer crate linked')
            (folder/'test-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
            assert receipt['exit_code']==0 and receipt['owned_group_absent'] and not receipt['timed_out'],out.decode()+err.decode()
            print(out.decode().strip(),flush=True)
        finally:
            shutil.rmtree(scratch)
            (folder/'cleanup.json').write_text(json.dumps(dict(owned_scratch=str(scratch),removed=not scratch.exists()),indent=2)+'\n')

if __name__=='__main__':main()
