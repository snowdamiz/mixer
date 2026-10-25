from pathlib import Path
import shutil,subprocess,json,datetime,hashlib,os
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent
dest=packet/'baseline-candidate';producer=root/'verification/hosted-worker-pending-terminal-consistency'
sha=lambda b:hashlib.sha256(b).hexdigest();write=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
for name in ['build.mjs','tsconfig.json']:
 dest.mkdir(exist_ok=True);shutil.copy2(packet/'candidate'/name,dest/name)
shutil.copytree(producer/'inputs/frozen-candidate/src',dest/'src',dirs_exist_ok=True)
shutil.copytree(packet/'candidate/test',dest/'test',dirs_exist_ok=True)
# The predecessor has no preserveOperationRow argument. This finite fixture
# action is unused by the six selected probes; remove it for baseline typing.
worker=dest/'test/worker.ts';s=worker.read_text();a=s.index("   case 'independentPreserveFence':{");b=s.index("   case 'rememberTerminal':{",a);worker.write_text(s[:a]+s[b:])
entries=[]
for p in sorted(dest.rglob('*')):
 if p.is_file():b=p.read_bytes();entries.append({'path':str(p.relative_to(dest)),'sha256':sha(b),'bytes':len(b)})
write(packet/'baseline-source-manifest.json',{'source':'frozen predecessor, approved controller/registry fixture only','entries':entries,'sourceDigest':sha(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in entries).encode())})
commands=json.loads((packet/'commands.json').read_text());node=subprocess.check_output(['which','node'],text=True).strip()
def run(name,args,env):
 started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with (packet/(name+'.stdout.log')).open('wb') as out,(packet/(name+'.stderr.log')).open('wb') as err:
  p=subprocess.run(args,cwd=root,stdout=out,stderr=err,env=env,timeout=60)
 commands.append({'name':name,'command':args,'cwd':str(root),'startedUTC':started,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':p.returncode,'stdout':str((packet/(name+'.stdout.log')).relative_to(root)),'stderr':str((packet/(name+'.stderr.log')).relative_to(root)),'stdoutEOF':True,'stderrEOF':True,'environment':{k:v for k,v in env.items() if k.startswith('MIXER_INDEPENDENT_')}});write(packet/'commands.json',commands);return p.returncode
assert run('baseline-build',[node,str(dest/'build.mjs')],dict(os.environ))==0
compiled=[]
for p in sorted((dest/'dist').rglob('*')):
 if p.is_file():b=p.read_bytes();compiled.append({'path':str(p.relative_to(dest)),'sha256':sha(b),'bytes':len(b)})
write(packet/'baseline-compiled-manifest.json',{'entries':compiled})
env={**os.environ,'MIXER_INDEPENDENT_FILTER':'probe-','MIXER_INDEPENDENT_REPORT':str(packet/'baseline-report.json')}
code=run('baseline-probes',[node,str(dest/'test/independent.mjs')],env)
print((packet/'baseline-probes.stdout.log').read_text());raise SystemExit(code)
