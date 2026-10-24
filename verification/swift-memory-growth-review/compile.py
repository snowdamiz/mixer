#!/usr/bin/env python3
from pathlib import Path
import gzip,json,os,sys
import run as r
def compile_context(label,tree,features='all',profile='debug',kind='runtime',unit=True):
    digest=r.sha(r.enc(r.manifest(tree)))
    scratch=Path(json.loads((r.HERE/'scratch.json').read_text())['path'])
    target=scratch/('target-source-'+digest)/(features+'-'+profile+'-'+('unit' if unit else 'production')+'-'+kind)
    env={'CARGO_TARGET_DIR':str(target)}
    argv=['cargo','test' if unit else 'rustc','--lib','--locked','--offline','--message-format=json']
    if unit:argv+=['--no-run']
    if features=='all':argv+=['--all-features']
    elif features=='swift':argv+=['--features','experimental-swift-reactor']
    if profile=='release':argv+=['--release']
    if kind=='mir':
        env.update(RUSTC_BOOTSTRAP='1',RUSTFLAGS='--emit=mir,link -Zmir-include-spans=yes')
    p,row=r.run(label+'-compile',argv,cwd=tree,env=env,source=tree)
    assert p.returncode==0,p.stderr.decode()
    artifacts=[json.loads(line) for line in p.stdout.decode().splitlines() if line.startswith('{')]
    binaries=[a['executable'] for a in artifacts if a.get('reason')=='compiler-artifact' and a.get('executable') and a.get('target',{}).get('name')=='mixer_vm']
    saved=[]
    for a in artifacts:
        if a.get('reason')=='compiler-artifact' and a.get('target',{}).get('name')=='mixer_vm':
            for f in a['filenames']:
                path=Path(f)
                if path.is_file():saved.append(dict(path=str(path),sha256=r.sha(path.read_bytes()),bytes=path.stat().st_size))
    r.write(r.HERE/'commands'/(label+'-compile')/'artifacts.json',saved)
    if kind=='mir':
        paths=list(target.rglob('mixer_vm*.mir'));assert len(paths)==1,paths
        data=paths[0].read_bytes();(r.HERE/(label+'.mir.gz')).write_bytes(gzip.compress(data,mtime=0))
        r.write(r.HERE/'commands'/(label+'-compile')/'mir.json',dict(path=str(paths[0]),sha256=r.sha(data),bytes=len(data)))
    if unit:
        assert len(binaries)==1,binaries
        binary=binaries[0]
        r.run(label+'-test-list',[binary,'--list'],cwd=tree,env=env,source=tree,binary=[binary])
        return binary,env
    return None,env
def main():
    scratch=Path(json.loads((r.HERE/'scratch.json').read_text())['path'])
    tree=scratch/'candidate'
    for features in ['all','swift']:
        for unit in [False,True]:compile_context('fresh-'+features+'-'+('unit' if unit else 'production'),tree,features,kind='mir',unit=unit)
    binary,env=compile_context('exact-runtime-all-debug',tree)
    p,_=r.run('exact-runtime-all-debug-growth',[binary,'memory_growth_operations::tests::','--nocapture','--test-threads=1'],cwd=tree,env=env,source=tree,binary=[binary]);assert p.returncode==0
if __name__=='__main__':main()
