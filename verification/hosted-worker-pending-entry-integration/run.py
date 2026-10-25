#!/usr/bin/env python3
from pathlib import Path
import datetime,json,subprocess,os,sys,hashlib
ROOT=Path(__file__).resolve().parents[2]; OWN=Path(__file__).resolve().parent
NODE='/Users/andreyyurlov/.local/share/fnm/node-versions/v22.23.3/installation/bin/node'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(name,args,env=None):
 d=OWN/'attempts'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');d.mkdir(parents=True)
 cmd=[NODE,*args];start=now()
 source=[]
 for directory in ['candidate','engine-regression','independent-regression','boundary-regression','component-regression']:
  for f in sorted((OWN/directory).rglob('*')):
   if f.is_file() and 'dist' not in f.parts:
    source.append({'path':str(f.relative_to(ROOT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
 (d/'source-manifest.json').write_text(json.dumps(source,indent=2)+'\n')
 with (d/'stdout.log').open('w') as out,(d/'stderr.log').open('w') as err:
  p=subprocess.run(cmd,cwd=ROOT,env={**os.environ,**(env or {})},stdout=out,stderr=err,timeout=300)
 for report in ({'entry':['entry-report.json'],'original71':['original-report.json']}.get(name,[])):
  if (OWN/report).exists():
   import shutil
   shutil.copyfile(OWN/report,d/report)
 if env and env.get('MIXER_V2_RUN_DIR'):
  for report in Path(env['MIXER_V2_RUN_DIR']).glob('*report.json'):
   import shutil
   shutil.copyfile(report,d/report.name)
 result={'name':name,'command':cmd,'cwd':str(ROOT),'startedUTC':start,'finishedUTC':now(),'exitCode':p.returncode,'stdout':str((d/'stdout.log').relative_to(ROOT)),'stderr':str((d/'stderr.log').relative_to(ROOT)),'stdoutEOF':True,'stderrEOF':True,'environment':env or {}}
 (d/'command.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return p.returncode
if __name__=='__main__':
 name=sys.argv[1];driver={'build':'candidate/build.mjs','original71':'candidate/test/run.mjs','entry':'candidate/test/entry.mjs','identity20':'candidate/test/owned-workerd-identity.test.mjs','closure':'audit-closure.mjs','versions':'tool-versions.mjs'}[name]
 env={'MIXER_CONTROLLER_TEST_REPORT':str(OWN/'original-report.json'),'MIXER_ENTRY_REPORT':str(OWN/'entry-report.json')}
 sys.exit(run(name,[str(OWN/driver)],env))
