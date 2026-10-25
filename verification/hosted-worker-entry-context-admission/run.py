#!/usr/bin/env python3
"""Capture each bounded local functional command, including failed attempts."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[2]
OWN=Path(__file__).resolve().parent
NODE='/Users/andreyyurlov/.local/share/fnm/node-versions/v22.23.3/installation/bin/node'
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def manifest():
    files=[]
    for f in sorted((OWN/'candidate').rglob('*')):
        if f.is_file(): files.append({'path':str(f.relative_to(ROOT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
    for name in ['vectors.json','acceptance.mjs']:
        f=ROOT/'verification/hosted-worker-controller-contract'/name
        files.append({'path':str(f.relative_to(ROOT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
    for relative in ['verification/hosted-worker-transport/cross-runtime-vectors.json','verification/hosted-worker-controller-implementation/jason-control-vectors.json']:
        f=ROOT/relative
        files.append({'path':relative,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
    return files
def run(name):
    driver={'build':'candidate/build.mjs','admission':'candidate/test/admission.mjs','entry45':'candidate/test/entry.mjs','controller28':'candidate/test/run.mjs','versions':'tool-versions.mjs','closure':'capture-closure.mjs'}[name]
    d=OWN/'attempts'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');d.mkdir(parents=True)
    env={'MIXER_CONTROLLER_TEST_REPORT':str(OWN/'controller-report.json'),'MIXER_ENTRY_REPORT':str(OWN/'entry-report.json'),'MIXER_ADMISSION_REPORT':str(OWN/'admission-report.json')}
    args=[NODE,str(OWN/driver)]; start=now()
    (d/'source-compiled-fixture-manifest.json').write_text(json.dumps(manifest(),indent=2)+'\n')
    with (d/'stdout.log').open('w') as out,(d/'stderr.log').open('w') as err:
        try:
            p=subprocess.run(args,cwd=ROOT,env={**os.environ,**env},stdout=out,stderr=err,timeout=300)
            code=p.returncode
        except subprocess.TimeoutExpired:
            code=124
    for report in {'admission':['admission-report.json'],'entry45':['entry-report.json'],'controller28':['controller-report.json'],'versions':['tool-versions.json'],'closure':['production-closure.json']}.get(name,[]):
        if (OWN/report).exists(): shutil.copyfile(OWN/report,d/report)
    result={'name':name,'command':args,'cwd':str(ROOT),'environment':env,'startedUTC':start,'finishedUTC':now(),'exitCode':code,'stdout':str((d/'stdout.log').relative_to(ROOT)),'stderr':str((d/'stderr.log').relative_to(ROOT)),'stdoutEOF':True,'stderrEOF':True,'sourceCompiledFixtureManifest':str((d/'source-compiled-fixture-manifest.json').relative_to(ROOT))}
    (d/'command.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True);return code
if __name__=='__main__': sys.exit(run(sys.argv[1]))
