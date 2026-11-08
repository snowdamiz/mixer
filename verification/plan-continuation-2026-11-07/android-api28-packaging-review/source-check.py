import ast,collections,contextlib,datetime,difflib,hashlib,io,json,pathlib,re,signal,types
B=pathlib.Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-53f259fe/verification/plan-continuation-2026-11-07/android-api28-packaging-fix');ROOT=B.parents[2];OUT=pathlib.Path(__file__).parent
R={'checks':{}}
def ident(p):
 p=pathlib.Path(p);b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(p):return json.loads(pathlib.Path(p).read_text())
receipt=load('/tmp/mixer-20261107-generated-java-pair8-03/receipt.json');external=load(OUT/'external-before.json')
for rel,w in receipt['source_inputs'].items():
 assert ident(ROOT/rel)==w,rel;external[str(ROOT/rel)]=w
R['checks']['pair8OwningSources']=len(receipt['source_inputs']);R['checks']['sourceInputsSHA256']=receipt['source_inputs_sha256']
# Token comparison supports manual semantic review; it is not runtime validation.
token=re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_$][\w$]*|\d+|\S',re.S)
def tokens(s):return [x for x in token.findall(s) if not x.startswith(('//','/*'))]
def calls(t,name):
 out=[]
 for i in range(len(t)-1):
  if t[i]!=name or t[i+1]!='(':continue
  depth=1;j=i+2
  while depth:
   depth+=int(t[j]=='(')-int(t[j]==')');j+=1
  out.append(t[i:j])
 return out
rel='native/android/tests/NativeLowerApiCompatibilityInstrumentation.java';a=(B/'compile-1/inputs'/rel).read_text();b=(B/'compile-2/inputs'/rel).read_text();ta,tb=tokens(a),tokens(b)
for name in ['check','status']:
 assert calls(ta,name)==calls(tb,name);R['checks'][name+'ExpressionsUnchanged']=len(calls(ta,name))
sa=[t for t in ta if t.startswith('"')];sb=[t for t in tb if t.startswith('"')];assert sa==sb;R['checks']['stringLiteralsUnchanged']=len(sa)
assert '->' not in b and '::' not in b
# Validate the entire new-file patch mechanically, not just its filenames.
patch=(B/'candidate.patch').read_text().splitlines();files={};current=None
for line in patch:
 if line.startswith('+++ b/'):
  current=line[6:];files[current]=[]
 elif line.startswith('+') and not line.startswith('+++'):
  assert current;files[current].append(line[1:])
assert set(files)==set(load(B/'frozen-ready-input-manifest.json')['sourceInputs'])
for rel,lines in files.items():assert '\n'.join(lines)+'\n'==(ROOT/rel).read_text()
R['checks']['patchReconstructsAllThreeSources']=True
# Exact product/source guards, bound above to all 101 pair8 owning inputs.
base=ROOT/'native/android/app/src/dev/mixer/android'
guards={
 'NativeEnvironmentV2.java':'if (Build.VERSION.SDK_INT < 36 || root.getContext() != activity) unsupported();',
 'NativeRenderer.java':'if(Build.VERSION.SDK_INT<36)throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);',
 'NativeEnvironmentPlatformV2.java':'if(Build.VERSION.SDK_INT<33) throw new IllegalStateException("effective animator listener requires API33");'}
R['checks']['productGuards']={}
for name,needle in guards.items():
 lines=(base/name).read_text().splitlines();assert sum(needle in l for l in lines)==1;R['checks']['productGuards'][name]={'line':next(i+1 for i,l in enumerate(lines) if needle in l),'source':needle,'identity':ident(base/name)}
assert 'refusal.code == AppearanceDescriptorV2.Error.unsupportedNativeOperation' in b and 'refusal.getClass() == AppearanceDescriptorV2.Failure.class' in b
assert '"unsupportedNativeOperation".equals(refusal.getMessage())' in b
assert all(x not in b for x in ['Unsafe','allocateInstance','setAccessible','requireV2Live','bindV2','prepareV2'])
# Exercise only AST-extracted custody functions with fake process/time/OS objects.
# These stubs never invoke native processes, inspect real PIDs, or send real signals.
tree=ast.parse((B/'prepare.py').read_text());functions=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['run','stop']],type_ignores=[])
class Timeout(Exception):pass
class Clock:
 def __init__(self):self.t=0
 def monotonic(self):return self.t
 def sleep(self,n):self.t+=n
class Child:
 pid=900000001
 def __init__(self,mode):self.mode=mode;self.returncode=0 if mode in ['success','leftover-group'] else None;self.group=mode!='success'
 def poll(self):return self.returncode
 def wait(self,timeout):
  if self.returncode is None:raise Timeout()
  return self.returncode
for mode in ['success','timeout','leftover-group','nonterminal']:
 clock=Clock();child=Child(mode);signals=[];launches=[];runout=OUT/('fake-'+mode);runout.mkdir(exist_ok=True)
 def killpg(pid,sig):
  assert pid==child.pid;signals.append(int(sig))
  if not child.group:raise ProcessLookupError()
  if sig and mode!='nonterminal':child.group=False;child.returncode=-int(sig)
 def popen(args,**kw):
  assert kw['start_new_session'] is True;launches.append({'args':args,'session':True});return child
 receipt={'commands':[]}
 env={'datetime':datetime,'time':clock,'os':types.SimpleNamespace(killpg=killpg),'signal':signal,'subprocess':types.SimpleNamespace(Popen=popen,DEVNULL=-3,STDOUT=-2,TimeoutExpired=Timeout),'START':0,'OUT':runout,'ENV':{},'RECEIPT':receipt,'flush':lambda:None,'identity':ident}
 exec(compile(functions,'audited-custody-functions','exec'),env)
 error=None
 with contextlib.redirect_stdout(io.StringIO()):
  try:env['run']('fake-only',['never-executed'],runout,timeout=.3)
  except RuntimeError as e:error=str(e)
 assert len(launches)==1 and len(receipt['commands'])==1
 if mode=='success':assert error is None and receipt['commands'][0]['cleanup']['groupAbsent']
 elif mode=='leftover-group':assert signals.count(int(signal.SIGTERM))==1 and not child.group
 elif mode=='timeout':assert error and receipt['commands'][0]['failure']=='timeout' and not child.group
 else:assert error and not receipt['commands'][0]['cleanup']['groupAbsent'] and not receipt['commands'][0]['cleanup']['leaderReaped']
 R['checks']['fakeCustody-'+mode]={'refusal':error,'cleanup':receipt['commands'][0]['cleanup'],'simulatedSignalCalls':signals,'realOSCalls':0}
(OUT/'external-before.json').write_text(json.dumps(external,indent=2)+'\n')
R['status']='PASS';R['finishedUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat();(OUT/'source-checks.json').write_text(json.dumps(R,indent=2)+'\n');print(json.dumps(R,indent=2))
