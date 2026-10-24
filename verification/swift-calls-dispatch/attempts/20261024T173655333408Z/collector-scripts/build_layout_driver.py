import collect as c
from pathlib import Path
import json,gzip,os
s=json.loads((c.HERE/'layout-tool-session.json').read_text());scratch=Path(s['scratch']);dest=scratch/'layout-driver';root=Path(s['sysroot']);source=c.HERE/'layout_driver.rs'
code,attempt,out,err=c.run(['/opt/homebrew/opt/rustup/bin/rustc','--edition=2021','--sysroot',str(root),'-C','prefer-dynamic','-C','rpath',str(source),'-o',str(dest)],env_extra={'RUSTC_BOOTSTRAP':'1'},label='metadata-layout-driver-build')
c.save(attempt/'layout_driver.rs',source.read_bytes())
if code==0:
 data=dest.read_bytes();c.save(attempt/'layout-driver.gz',gzip.compress(data,mtime=0));c.save(c.HERE/'layout-driver-build.json',{'attempt':str(attempt.relative_to(c.HERE)),'binary':str(dest),'sha256':c.sha(data),'bytes':len(data),'sourceSHA256':c.sha(source.read_bytes()),'sysroot':str(root),'status':'metadata-tool-only'})
raise SystemExit(code)
