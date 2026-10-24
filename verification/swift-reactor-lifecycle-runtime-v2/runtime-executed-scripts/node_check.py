#!/usr/bin/env python3
"""Verify the previously qualified exact Node/Apple closure before oracle runs."""
from pathlib import Path
import datetime,json,os,shutil
import runtime_support as s

PROVENANCE=s.ROOT/'verification/swift-calls-dispatch-node-oracle-qualification/node-provenance.json'

def verify(env,folder):
    data=s.read(PROVENANCE)
    assert not {k:v for k,v in env.items()if v and(k.startswith('NODE_')or 'DYLD_'in k or k in ['LD_PRELOAD','LD_LIBRARY_PATH'])}
    assert Path(shutil.which('node',path=env['PATH'])).resolve()==Path(data['actualPath'])
    assert s.digest(data['actualPath'])==data['executableSHA256']
    source=s.HERE/'candidate'/data['oracleSource']
    assert s.digest(source)==data['oracleSourceSHA256']
    text=source.read_text();a=text.index('let script = r#"')+len('let script = r#"');b=text.index('"#;',a)
    assert text[a:b]==data['script']and s.sha(text[a:b].encode())==data['scriptSHA256']
    assert str(Path(data['logicalSystemCacheDirectory']).resolve())==data['systemCacheDirectory']
    root=Path(data['systemCacheDirectory']);assert {str(p)for p in root.iterdir()}==set(data['systemCacheFiles'])
    for item in [data['loader'],data['systemVersion']]:assert s.digest(item['path'])==item['sha256']
    for path,item in data['physicalLoadedSystemFiles'].items():assert Path(path).stat().st_size==item['bytes']and s.digest(path)==item['sha256']
    for path,item in data['systemCacheFiles'].items():assert Path(path).is_file()and Path(path).stat().st_size==item['bytes']and s.digest(path)==item['sha256']
    s.save(folder/'qualified-node-check.json',{'provenanceSHA256':s.digest(PROVENANCE),'nodeSHA256':data['executableSHA256'],'version':data['version'],'oracleSourceSHA256':data['oracleSourceSHA256'],'scriptSHA256':data['scriptSHA256'],'fullLoaderAndCacheFileSetMatched':True,'systemCacheFiles':len(data['systemCacheFiles']),'systemCacheBytes':data['systemCacheBytes'],'injectionEnvironmentEmpty':True,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()})
