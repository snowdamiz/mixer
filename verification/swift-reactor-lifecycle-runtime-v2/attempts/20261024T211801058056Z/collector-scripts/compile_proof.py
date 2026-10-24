#!/usr/bin/env python3
"""Four fresh unit queries with the exact retained metadata-only driver."""
from pathlib import Path
import datetime,gzip,json,sys,traceback
import collect as c

session=c.read_json(c.HERE/'metadata-tool-session.json')
assert c.sha(Path(session['binary']).read_bytes())==session['sha256']=='80c8c8410b4e79120dec1368ad368f869119aeface40f8660e7bd19527c878b7'

def main():
    results=[]
    for features in ['swift','all']:
        for profile in ['debug','release']:
            name=features+'-'+profile+'-unit'
            output=Path(session['scratch'])/(name+'.jsonl')
            flags=['--no-default-features']+(['--features','experimental-swift-reactor']if features=='swift'else['--all-features'])+(['--release']if profile=='release'else[])
            code,attempt,out,err=c.run(['cargo','rustc','--lib','--locked','--offline',*flags,'--','--emit=mir','-Zmir-include-spans=yes','--test'],env_extra={'RUSTC_BOOTSTRAP':'1','RUSTC_WRAPPER':session['binary'],'MIXER_LAYOUT_SYSROOT':session['sysroot'],'MIXER_LAYOUT_OUTPUT':str(output),'DYLD_LIBRARY_PATH':str(Path(session['sysroot'])/'lib')},label='exact-query-'+name)
            row={'context':name,'attempt':str(attempt.relative_to(c.HERE)),'exitCode':code,'sourceClosure':c.sha(c.enc(c.manifest(c.HERE/'candidate'))),'metadataDriverSHA256':session['sha256'],'runtimeExecuted':False,'reusedRetainedMetadataBinary':True,'sharedToolchainModified':False}
            if output.exists():
                raw=output.read_bytes();c.save(attempt/'exact-layouts.jsonl.gz',gzip.compress(raw,mtime=0));output.unlink();row.update(sha256=c.sha(raw),bytes=len(raw),records=len(raw.splitlines()))
            c.save(c.HERE/('exact-query-'+name+'.json'),row);results.append(row);c.save(c.HERE/'compiler-results.json',results)
            assert code==0,'preserved compiler failure; runtime prohibited'
    print('Four compiler-only unit contexts complete',flush=True)

if __name__=='__main__':main()
