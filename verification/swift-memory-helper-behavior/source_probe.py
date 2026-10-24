#!/usr/bin/env python3
"""Capture exact unoptimized compiler MIR/expanded source; invoke no engine."""
from pathlib import Path
import sys
import json,gzip,tarfile
from run import run,SCRATCH,HERE,b
STAGE=sys.argv[1] if len(sys.argv)>1 else 'draft'
for unit in [False,True]:
 label='unit' if unit else 'production'
 args=['cargo','test','--lib','--no-run','--locked','--offline','--all-features'] if unit else ['cargo','rustc','--lib','--locked','--offline','--all-features','--','--emit=mir','-Zmir-include-spans=yes']
 extra={'RUSTC_BOOTSTRAP':'1'}
 if unit:extra['RUSTFLAGS']='--emit=mir,link -Zmir-include-spans=yes'
 p=run(STAGE+'-'+label+'-mir',args,SCRATCH/'candidate',extra);assert p.returncode==0
 paths=[q for q in (SCRATCH/('target-'+STAGE+'-'+label+'-mir')/'debug/deps').glob('*.mir') if '::memory_operation(' in q.read_text()]
 assert len(paths)==1,paths
 (HERE/(label+'.mir')).write_bytes(paths[0].read_bytes())
 with gzip.open(HERE/(STAGE+'-'+label+'.mir.gz'),'wb') as z:z.write(paths[0].read_bytes())
 print(label,paths[0],flush=True)
