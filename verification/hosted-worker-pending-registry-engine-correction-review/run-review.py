from pathlib import Path
import datetime
import hashlib
import json
import platform
import shutil
import subprocess

OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[1]
CANDIDATE=OWN/'candidate'
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(data): return hashlib.sha256(data).hexdigest()
entries=[]
for path in sorted(CANDIDATE.rglob('*')):
    if path.is_file() and 'dist' not in path.relative_to(CANDIDATE).parts:
        data=path.read_bytes()
        entries.append({'path':str(path.relative_to(CANDIDATE)),'sha256':sha(data),'bytes':len(data)})
digest=sha(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in entries).encode())
(OWN/'source-manifest.json').write_text(json.dumps({'algorithm':'sha256','sourceDigest':digest,'entries':entries},indent=2)+'\n')
node=shutil.which('node')
workerd=ROOT/'hosted-worker-controller/node_modules/@cloudflare/workerd-darwin-arm64/bin/workerd'
versions={'node':subprocess.check_output([node,'--version'],text=True).strip(),'python':platform.python_version(),'platform':platform.system(),'architecture':platform.machine(),'workerdBinary':str(workerd),'workerd':subprocess.check_output([str(workerd),'--version'],text=True).strip()}
for package in ['miniflare','typescript','@cloudflare/workers-types']:
    versions[package]=json.loads((ROOT/'hosted-worker-controller/node_modules'/package/'package.json').read_text())['version']
(OWN/'tool-versions.json').write_text(json.dumps(versions,indent=2)+'\n')
commands=[]
for label,script in [('build',CANDIDATE/'build.mjs'),('test',CANDIDATE/'test/review.mjs')]:
    command=[node,str(script)]
    started=now()
    result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,timeout=60)
    (OWN/(label+'.stdout.log')).write_text(result.stdout)
    (OWN/(label+'.stderr.log')).write_text(result.stderr)
    commands.append({'command':command,'cwd':str(ROOT),'startedUTC':started,'finishedUTC':now(),'exitCode':result.returncode,'stdoutEOF':True,'stderrEOF':True,'timeoutSeconds':60})
    print(json.dumps({'command':label,'exitCode':result.returncode,'stdoutBytes':len(result.stdout.encode()),'stderrBytes':len(result.stderr.encode())}))
    if result.returncode:
        print(result.stdout)
        print(result.stderr)
        break
(OWN/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
print(json.dumps({'sourceDigest':digest,'commands':len(commands)}))
if any(c['exitCode'] for c in commands): raise SystemExit(1)
