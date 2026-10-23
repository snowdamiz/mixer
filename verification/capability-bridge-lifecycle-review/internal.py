#!/usr/bin/env python3
"""Labelled private gate/fault probes; reuses frozen Debug products, no rebuild."""
import hashlib,json,os,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(value,message):
    if not value:raise RuntimeError(message)
def main():
    public=json.loads((HERE/'2026-10-23-public/receipt.json').read_text())
    source=Path(public['immutable_source']);work=HERE/'.build/internal';work.mkdir(parents=True,exist_ok=False)
    out=HERE/'2026-10-23-internal';out.mkdir(exist_ok=False)
    def unchanged():
        for name,digest in public['owner_source'].items():
            require(sha(source/name)==digest,'immutable source '+name)
            require(sha(ROOT/name)==digest,'live source '+name)
        for record in list(public['libraries'].values())+[public['native_archive']]:require(sha(Path(record['path']))==record['sha256'],'reused artifact unchanged')
    unchanged();captured=work/'InternalProbe.swift';captured.write_bytes((HERE/'InternalProbe.swift').read_bytes())
    base=next(c['argv'] for c in public['commands'] if c['name']=='debug-link')
    binary=work/'internal-probe';command=base[:-3]+[str(captured),'-o',str(binary)]
    receipt=dict(status='running',owner_source_manifest_sha256=public['owner_source_manifest_sha256'],immutable_source=str(source),
        original_probe_sha256=sha(captured),driver_sha256=sha(Path(__file__)),library=public['libraries']['debug'],native_archive=public['native_archive'],commands=[],
        scope='Review-only @testable private gates/faults against unmodified frozen Debug products, real concrete storage; manual nativeDidDrain is synthetic, stale native close deliberately violates public ownership.',
        limitations=['No production source mutation or hooks','Manual native-drain gate is not actual resource exit','Forced internal stale handle is not a public reproduction','Failed-close probe intentionally retains one owner/permit in its isolated subprocess','No additional package graph, devices, runtime OS destruction, activation or GA proof'])
    def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def run(name,argv,timeout=30,fragment=None):
        unchanged();began=time.monotonic()
        try:r=subprocess.run(argv,cwd=source,env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);raw,code=r.stdout,r.returncode
        except subprocess.TimeoutExpired as error:raw,code=(error.stdout or b'')+b'\nprivate probe timeout\n',124
        log=out/(name+'.log');log.write_bytes(raw);receipt['commands'].append(dict(name=name,argv=argv,cwd=str(source),exit_code=code,timeout_seconds=timeout,seconds=time.monotonic()-began,log=str(log.relative_to(ROOT)),sha256=sha(log)));save()
        require(code==0,name+' unexpected exit '+str(code))
        if fragment:require(fragment.encode() in raw,name+' expected output')
        unchanged();print(name+': '+str(code),flush=True)
    save()
    try:
        run('internal-link',command)
        for mode in ['gates','close-failure']:run(mode,[str(binary),mode],fragment='internal lifecycle review '+mode+' passed')
        require(captured.read_bytes()==(HERE/'InternalProbe.swift').read_bytes(),'captured private probe unchanged')
        receipt.update(status='private gate/fault checks passed',source_export_and_artifacts_unchanged=True,binary=dict(path=str(binary),sha256=sha(binary)))
    except Exception as error:receipt.update(status='failed private check preserved',problem=str(error));save();raise
    save();print('receipt_sha256 '+sha(out/'receipt.json'))
if __name__=='__main__':main()
