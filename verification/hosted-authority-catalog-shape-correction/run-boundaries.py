#!/usr/bin/env python3
"""Record exact model-input execution and preserve every numbered attempt."""
import argparse, datetime, gzip, hashlib, json, os, pathlib, platform, shutil, subprocess, sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def manifest(path):
    return [{'path':str(p.relative_to(path)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
            for p in sorted(path.rglob('*')) if p.is_file()]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args()
    out=pathlib.Path(args.out);out=out if out.is_absolute() else HERE/out
    out.mkdir(parents=True,exist_ok=False)
    shutil.copytree(HERE/'candidate',out/'source');shutil.copyfile(HERE/'boundary-tests.py',out/'executed-boundary-tests.py');shutil.copyfile(__file__,out/'executed-driver.py')
    source=manifest(out/'source');(out/'source-manifest.json').write_text(json.dumps(source,indent=2)+'\n')
    env=dict(os.environ,MIXER_SHAPE_PACKET=str(HERE),PYTHONDONTWRITEBYTECODE='1')
    argv=[sys.executable,'-B',str(out/'executed-boundary-tests.py'),'--out',str(out/'results')]
    record={'argv':argv,'cwd':str(ROOT),'started_utc':utc(),'environment_overrides':{'MIXER_SHAPE_PACKET':str(HERE),'PYTHONDONTWRITEBYTECODE':'1'}}
    p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,env=env,timeout=120)
    record.update(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,stdout_sha256=sha(p.stdout.encode()),stderr_sha256=sha(p.stderr.encode()),finished_utc=utc())
    (out/'command.json').write_text(json.dumps(record,indent=2)+'\n')
    unchanged=source==manifest(HERE/'candidate') and (out/'executed-boundary-tests.py').read_bytes()==(HERE/'boundary-tests.py').read_bytes()
    receipt={'argv':sys.argv,'observed_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             'observed_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
             'python':sys.version,'python_executable':str(pathlib.Path(sys.executable).resolve()),'platform':platform.platform(),
             'source_digest':sha(json.dumps(source,sort_keys=True,separators=(',',':')).encode()),
             'source_unchanged_during_execution':unchanged,'success':p.returncode==0 and unchanged,
             'scope':'raw-input model only; no database, native, phone or production action'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(p.stdout,end='');print(json.dumps(receipt,indent=2))
    return 0 if receipt['success'] else 1
if __name__=='__main__':sys.exit(main())
