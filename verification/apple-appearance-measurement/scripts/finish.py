#!/usr/bin/env python3
"""Bind analysis and executable verification to stable retained source inputs."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def file(path):return dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def sources():
 paths=[p for folder in ['instrumented-sdk','harness','scripts','comparison-inputs'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'xcuserdata' not in p.parts]
 return [file(p) for p in sorted(paths)]
def collection(entries):return hashlib.sha256(json.dumps(entries,sort_keys=True,separators=(',',':')).encode()).hexdigest()
start=sources();commands=[]
for name,script in [('analysis-tests','test-analysis.py'),('analysis','analyze.py'),('verification','verify.py')]:
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();args=[sys.executable,str(ROOT/'scripts'/script)]
 log=ROOT/'logs'/(name+'.log')
 with log.open('w') as out: result=subprocess.run(args,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
 commands.append(dict(name=name,argv=args,cwd=str(ROOT),startedUTC=started,finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  exitCode=result.returncode,output=str(log.relative_to(ROOT)),outputSHA256=hashlib.sha256(log.read_bytes()).hexdigest()))
 (ROOT/'postprocess-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 if result.returncode:raise RuntimeError(name+' failed: '+log.read_text())
 print(name+' passed',flush=True)
end=sources();assert start==end,'source changed during postprocessing'
(ROOT/'source-lock.json').write_text(json.dumps(dict(format='mixer.apple-appearance-measurement-sources.1',files=start,sourceCollectionSHA256=collection(start),sourceStableDuringPostprocess=True,
 scope='Post-run retained build sources, analysis/verification scripts and provisional comparison freeze; source hashes do not assert cryptographic build attestation.'),indent=2)+'\n')
