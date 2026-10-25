from pathlib import Path
import subprocess,json,datetime,os,hashlib,importlib.util
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent
write=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
sha=lambda b:hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('review_prepare',packet/'prepare.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
write(packet/'frozen-before-run.json',module.checks())
entries=[]
for p in sorted((packet/'candidate').rglob('*')):
 if p.is_file() and 'dist' not in p.relative_to(packet/'candidate').parts:
  b=p.read_bytes();entries.append({'path':str(p.relative_to(packet/'candidate')),'sha256':sha(b),'bytes':len(b)})
write(packet/'source-manifest.json',{'entries':entries,'sourceDigest':sha(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in entries).encode())})
commands=json.loads((packet/'commands.json').read_text()) if (packet/'commands.json').exists() else []
def run(name,args,env=None):
 started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with (packet/(name+'.stdout.log')).open('wb') as out,(packet/(name+'.stderr.log')).open('wb') as err:
  p=subprocess.Popen(args,cwd=root,stdout=out,stderr=err,env=env)
  try:code=p.wait(timeout=120)
  except subprocess.TimeoutExpired:p.kill();code=p.wait();raise
 commands.append({'name':name,'command':args,'cwd':str(root),'startedUTC':started,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':code,'signal':-code if code<0 else None,'stdout':str((packet/(name+'.stdout.log')).relative_to(root)),'stderr':str((packet/(name+'.stderr.log')).relative_to(root)),'stdoutEOF':True,'stderrEOF':True,'environment':{k:v for k,v in (env or {}).items() if k.startswith('MIXER_INDEPENDENT_')}})
 write(packet/'commands.json',commands);return code
node=subprocess.check_output(['which','node'],text=True).strip()
code=run('build',[node,str(packet/'candidate/build.mjs')])
if code:print((packet/'build.stderr.log').read_text());raise SystemExit(code)
compiled=[]
for p in sorted((packet/'candidate/dist').rglob('*')):
 if p.is_file():b=p.read_bytes();compiled.append({'path':str(p.relative_to(packet/'candidate')),'sha256':sha(b),'bytes':len(b)})
write(packet/'compiled-manifest.json',{'entries':compiled})
env=dict(os.environ)
if len(os.sys.argv)>1:env['MIXER_INDEPENDENT_FILTER']=os.sys.argv[1]
env['MIXER_INDEPENDENT_REPORT']=str(packet/('probe-report.json' if len(os.sys.argv)>1 else 'independent-report.json'))
code=run('probes' if len(os.sys.argv)>1 else 'test',[node,str(packet/'candidate/test/independent.mjs')],env)
write(packet/'frozen-after-run.json',module.checks())
print((packet/('probes.stdout.log' if len(os.sys.argv)>1 else 'test.stdout.log')).read_text())
raise SystemExit(code)
