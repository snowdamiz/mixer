"""Pure checked integers only. No product crate or runtime is linked."""
import gzip
import json
import re
import shutil
from prepare import HERE,CONTROL,canonical,sha
from run import RUSTC,bounded

def main():
    assert not (HERE/'seal.json').exists()
    folder=HERE/'commands/scalar-checked';folder.mkdir(parents=True,exist_ok=False)
    scratch=HERE/'owned-work/scalar-checked';scratch.mkdir(parents=True,exist_ok=False)
    text=(HERE/'overlay'/CONTROL).read_text()
    declaration=re.search(r'const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =\n    [^;]+;',text)[0]
    source=declaration+'''
fn emission(b:u64,e:u64)->Option<u64>{
    19_537u64.checked_add(299_377u64.checked_mul(b)?)?.checked_add(32u64.checked_mul(e)?)
}
fn quote(b:u64,e:u64)->Option<u64>{
    SNAPSHOT_FIXED_EXECUTION_WORK_V1.checked_add(16_384)?.checked_add(emission(b,e)?)
}
fn main(){
    assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
    assert_eq!(451_703_621u64.checked_add(33_613).and_then(|n|n.checked_add(68_781))
        .and_then(|n|n.checked_add(7_155)).and_then(|n|n.checked_add(1_272)),Some(SNAPSHOT_FIXED_EXECUTION_WORK_V1));
    let mut checks=2;
    for b in [0u64,1,2,3,7,255,994,1_000_000,u64::MAX/299_377,u64::MAX/299_377+1,u64::MAX] {
      for e in [0u64,1,31,32,4096,1_000_000,u64::MAX/32,u64::MAX/32+1,u64::MAX] {
        let wide=451_814_442u128+16_384+19_537+299_377u128*u128::from(b)+32*u128::from(e);
        let expected=if wide<=u64::MAX as u128{Some(wide as u64)}else{None};
        assert_eq!(quote(b,e),expected); checks+=1;
        if let Some(price)=expected {
          for limit in [0u64,price.saturating_sub(1),price,price.saturating_add(1),1_000_000_000,u64::MAX] {
            assert_eq!(quote(b,e).filter(|n|*n<=limit).is_some(),wide<=u128::from(limit));checks+=1;
          }
        }
      }
    }
    assert!(quote(1,0).unwrap()<=1_000_000_000);checks+=1;
    assert!(quote(994,0).unwrap()<=1_000_000_000);checks+=1;
    assert!(quote(2_000,0).unwrap()>1_000_000_000);checks+=1;
    assert!(u64::MAX.checked_add(1_272).is_none());checks+=1;
    println!("{} checked arithmetic controls passed; synthetic integer geometry only",checks);
}
'''
    (folder/'scalar-source.rs').write_text(source);(scratch/'scalar.rs').write_text(source)
    env={'PATH':'/usr/bin:/bin','TMPDIR':str(scratch)}
    version,err,vr=bounded([str(RUSTC),'--version','--verbose'],env,HERE,10)
    (folder/'compiler-version-stdout').write_bytes(version)
    try:
        argv=[str(RUSTC),'--crate-name','snapshot_work_scalar','--edition=2021','-C','overflow-checks=yes',str(scratch/'scalar.rs'),'-o',str(scratch/'scalar')]
        out,err,receipt=bounded(argv,env,HERE,30)
        (folder/'stdout.gz').write_bytes(gzip.compress(out,mtime=0));(folder/'stderr').write_bytes(err)
        receipt.update(schema=1,compiler_sha256=sha(RUSTC.read_bytes()),compiler_version=version.decode(),
            compiler_version_command=vr,source_sha256=sha(source.encode()),fixed_declaration_sha256=sha(declaration.encode()),
            stdout_sha256=sha(out),stderr_sha256=sha(err),scope='standalone checked integers; no Mixer dependency')
        (folder/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        assert receipt['exit_code']==0 and receipt['owned_group_absent'] and not receipt['timed_out'],err.decode()
        out,err,receipt=bounded([str(scratch/'scalar')],env,scratch,10)
        (folder/'test-stdout').write_bytes(out);(folder/'test-stderr').write_bytes(err)
        receipt.update(schema=1,source_sha256=sha(source.encode()),executable_sha256=sha((scratch/'scalar').read_bytes()),
            stdout_sha256=sha(out),stderr_sha256=sha(err),scope='standalone checked integer arithmetic only')
        (folder/'test-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        assert receipt['exit_code']==0 and receipt['owned_group_absent'] and not receipt['timed_out'],out.decode()+err.decode()
        print(out.decode().strip())
    finally:
        shutil.rmtree(scratch)
        (folder/'cleanup.json').write_text(json.dumps(dict(owned_scratch=str(scratch),removed=not scratch.exists()),indent=2)+'\n')

if __name__=='__main__':main()
