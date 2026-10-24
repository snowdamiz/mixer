from pathlib import Path
import datetime,hashlib,json,os,re,subprocess,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/swift-executor-construction/candidate-2'
BUILD=HERE/'build';BUILD.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((PRODUCER/'receipt.json').read_text());manifest=json.loads((PRODUCER/'source-manifest.json').read_text())
archive=PRODUCER/r['archive']['path']
if sha(archive)!=r['archive']['sha256']:raise RuntimeError('archive mismatch')
with tarfile.open(archive) as t:t.extractall(BUILD,filter='data')
print('manifest type',type(manifest).__name__,flush=True)
commands=[];status='failed';counts={}
env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],CARGO_TARGET_DIR=str(BUILD/'target'))
def run(name,args):
 p=subprocess.run(args,cwd=BUILD/'vm',env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
 log=HERE/(name+'.log');log.write_bytes(p.stdout)
 commands.append({'name':name,'argv':args,'exit':p.returncode,'log':str(log.relative_to(ROOT)),'sha256':sha(log)})
 print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(p.stdout.decode(errors='replace')[-4000:])
 return p.stdout.decode()
try:
 run('rustc-version',['rustc','-Vv']);run('cargo-version',['cargo','-V'])
 for mode in ['debug','release']:
  args=['cargo','test','--locked','--offline','--all-features']+(['--release'] if mode=='release' else [])
  output=run('all-features-'+mode,args)
  rows=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',output)
  counts[mode]={'passed':sum(int(x[0]) for x in rows),'failed':sum(int(x[1]) for x in rows),'ignored':sum(int(x[2]) for x in rows),'suite_summaries':len(rows)}
 status='passed-all-features-host'
finally:
 out={'status':status,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevision':r['revision'],'producerSourceTreeSHA256':r['source_tree_digest'],'producerReceiptSHA256':sha(PRODUCER/'receipt.json'),'archiveSHA256':sha(archive),'commands':commands,'counts':counts,'scope':'Broader all-feature host regression against exact archived constructor candidate2. Ordinary ignored tests remain ignored; no full Swift target initialize/invoke, physical device or GA qualification.'}
 (HERE/'qualification.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print('PASS',counts)
