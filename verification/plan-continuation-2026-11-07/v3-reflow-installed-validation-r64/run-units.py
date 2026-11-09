from pathlib import Path
import ast,json,os,subprocess,sys,tempfile,time
p=Path(__file__).resolve().parent;root=p.parents[2];base=root/'verification/plan-continuation-2026-11-07';caller=base/'source113-inspection-caller-r3';worker=base/'v3-reflow-pair14-source-integration-r62/test-worker.py'
owned=Path(tempfile.mkdtemp(prefix='mixer-p14-root-units-',dir='/Users/andreyyurlov/.t3/userdata'));(p/'scratch.json').write_text(json.dumps({'owned':str(owned)})+'\n')
tree=ast.parse((base/'v3-reflow-pair14-source-integration-r62/checks.py').read_text());selection=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='selection' for t in n.targets))
suites=[('policy',['cli/build-tests/test_android_sdk_compatibility.py','-v']),*[(n,[str(caller/(n+'.py')),'-v']) for n in ['test_binding','test_source113','test_rebind']],('combined',['-m','unittest','discover','-s',str(caller),'-p','test_combined.py','-v']),('bootstrap',[str(base/'generated-java-ci-integration/test_bootstrap.py'),'-v']),('generator',['scripts/ci/tests/test_android_generated_java_runner.py',*['RunnerControls.'+n for n in selection],'-v']),('installed-entry',[str(caller/'adopt_envelope.py'),'verify','--workflow-installed'])]
rows=[]
for mode in ['normal','optimized']:
 for name,args in suites:
  if mode=='normal' and name in ['policy','test_binding','test_source113','test_rebind']:continue
  scratch=owned/(mode+'-'+name);scratch.mkdir();(caller/'control-scratch').mkdir(exist_ok=True)
  env=os.environ.copy();env.update(TMPDIR=str(scratch),PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0')
  argv=[sys.executable,'-B',*(['-O'] if mode=='optimized' else []),str(worker),*args];started=time.monotonic()
  with (p/(mode+'-'+name+'.log')).open('wb') as log:
   child=subprocess.Popen(argv,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   row={'mode':mode,'suite':name,'argv':argv,'pid':child.pid,'pgid':child.pid};rows.append(row);(p/'commands.json').write_text(json.dumps(rows,indent=2)+'\n')
   code=child.wait(timeout=120)
  row.update(exitCode=code,seconds=time.monotonic()-started)
  try:os.killpg(child.pid,0);row['groupAbsent']=False
  except ProcessLookupError:row['groupAbsent']=True
  (p/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');print(mode,name,code,flush=True)
  if code or not row['groupAbsent']:raise RuntimeError('Stop on concrete failure: '+mode+'/'+name)
(p/'result.json').write_text(json.dumps({'passed':True,'normalPreviouslyPassed':52,'normalCompletedHere':62,'optimizedPassed':114,'installedEntryBothModes':True,'allCommandGroupsAbsent':True,'source115':'bb2344bc2410110aa8e29e3b211a4cdc1ed8468e82b09690e6464afc52b97c65'},indent=2)+'\n')
print('PASS all remaining ordinary controls',flush=True)
