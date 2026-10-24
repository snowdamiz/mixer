#!/usr/bin/env python3
from pathlib import Path
import gzip,sys
from run import run,SCRATCH,HERE,sha,enc,manifest,digest,target_dir
label=sys.argv[1];features=sys.argv[2]if len(sys.argv)>2 else'all';flags=['--all-features']if features=='all'else['--features','experimental-swift-reactor']
for config in ['production','unit']:
 name=f'{label}-{features}-{config}-mir'
 args=['cargo','rustc','--lib','--locked','--offline',*flags,'--','--emit=mir','-Zmir-include-spans=yes']if config=='production'else['cargo','test','--lib','--no-run','--locked','--offline',*flags]
 extra={'RUSTC_BOOTSTRAP':'1'}
 if config=='unit':extra['RUSTFLAGS']='--emit=mir,link -Zmir-include-spans=yes'
 target=target_dir(SCRATCH/'candidate/vm',args,extra,name);before={str(p):sha(p.read_bytes())for p in target.rglob('*.mir')}if target.exists()else{}
 p=run(name,args,SCRATCH/'candidate/vm',extra);assert p.returncode==0
 changed=[p for p in target.rglob('*.mir')if before.get(str(p))!=sha(p.read_bytes())];assert len(changed)==1,[str(p)for p in changed]
 source=changed[0];data=source.read_bytes();output=HERE/(f'{label}-{features}-{config}.mir.gz');output.write_bytes(gzip.compress(data,mtime=0))
 (HERE/'commands'/name/'mir.json').write_bytes(enc(dict(path=str(source),bytes=len(data),sha256=sha(data),saved=output.name)))
 print('saved',output.name,len(data),flush=True)
