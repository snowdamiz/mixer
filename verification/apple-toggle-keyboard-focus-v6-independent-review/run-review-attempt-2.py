#!/usr/bin/env python3
"""Host-only review recorder. No Git, build, native instance, UI or product operations."""
import ast, datetime, difflib, hashlib, json, os, pathlib, platform, re, shutil, subprocess, sys, time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=ROOT/'verification/apple-toggle-keyboard-focus-v6-preparation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
seal=P/'packet-seal.json';selection=ROOT/'verification/apple-toggle-keyboard-focus-v5-root-review/v6-repair-selection.json'
assert sha(seal)=='5b2743fd61dbabc95abc6e50468347efe406953fb1314785b17013922b6438fd'
assert sha(selection)=='a687f64d09bc04df73842b3a45a4014551497a452cdf5092cd24ee60cbb9a3d7'
bindings=json.loads(seal.read_bytes())['files'];assert len(bindings)==184
before={n:sha(ROOT/n) for n in bindings};assert before==bindings
priorseal=ROOT/'verification/apple-toggle-keyboard-focus-v5-independent-review/review-seal.json'
assert sha(priorseal)=='dbe9f176e1f32d418fb70592b976dcb3ff84789d10104d50816b720c54d7af6d'
priorbindings=json.loads(priorseal.read_bytes())['files'];assert all(sha(ROOT/n)==d for n,d in priorbindings.items())
commands=[]
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
def command(name,argv,expected=0,count=None,failures=None):
 argv=list(map(str,argv));started=time.monotonic()
 try:
  p=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
  result=dict(name=name,argv=argv,cwd=str(ROOT),exitCode=p.returncode,stdout=p.stdout,stderr=p.stderr,elapsedSeconds=time.monotonic()-started)
 except subprocess.TimeoutExpired as e:
  result=dict(name=name,argv=argv,cwd=str(ROOT),exitCode=None,stdout=str(e.stdout),stderr=str(e.stderr),elapsedSeconds=time.monotonic()-started,timedOut=True)
 match=re.search(r'Ran (\d+) tests? in ',result['stderr']);ran=int(match.group(1)) if match else None
 actual=sorted(set(re.findall(r'^FAIL: (test_\w+)',result['stderr'],re.MULTILINE)))
 result.update(expectedExitCode=expected,testsRun=ran,expectedTestsRun=count,expectedFailureMethods=failures,actualFailureMethods=actual)
 result['expectedOutcomeMatched']=result['exitCode']==expected and (count is None or count==ran) and (failures is None or failures==actual)
 commands.append(result)
 (HERE/(name+'.stdout')).write_text(result['stdout']);(HERE/(name+'.stderr')).write_text(result['stderr'])
 print(json.dumps({k:result[k] for k in ['name','exitCode','testsRun','expectedOutcomeMatched']}),flush=True)
 return result
command('python-version',[sys.executable,'--version'])
compiler=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')
command('swift-version',[compiler,'--version'])
command('sealed-preflight',[sys.executable,'-B',P/'run.py','verify'])
command('frozen-stale-check',[sys.executable,'-B',P/'offline_checks.py','--check'])
command('fresh-attempt-2',[sys.executable,'-B',HERE/'test_fresh.py'],count=10)
wrapper=[sys.executable,'-B',HERE/'run_host_group.py']
groups=[('producer-v6-8','test_v6.py',8),('producer-v5-adapted-26','test_v5_independent26.py',26),('producer-v5-18','test_v5.py',18),('producer-independent-17','test_independent_adapted.py',17),('producer-v6-original-44','execute_v5_44.py',44),('producer-v4-39','execute_legacy_v4.py',39),('producer-v4-original-44','execute_legacy_v4_44.py',44),('producer-v3-original-44','execute_v3_controls.py',44)]
for name,file,count in groups:command(name,[*wrapper,P/file],count=count)
command('producer-v2-29',[*wrapper,P.parent/'apple-toggle-keyboard-focus-v2/test_keyboard.py'],count=29)
command('historical-v3-findings',[*wrapper,P/'test_independent_adapted.py','--sealed-v3'],expected=1,count=17,failures=['test_CONTRACT_replay_rejects_regressing_host_receipt_time','test_CONTRACT_wrong_route_search_cannot_satisfy_selected_route','test_CONTRACT_wrong_target_poll_cannot_supply_enabled_window'])
command('historical-v5-finding',[*wrapper,P/'execute_legacy_v5_review.py'],expected=1,count=26,failures=['test_CONTRACT_destination_captured_before_tap_return_cannot_complete'])
command('historical-v4-native-replay',[sys.executable,'-B',P.parent/'apple-toggle-keyboard-focus-v4/replay.py'])
command('historical-v4-analysis-check',[sys.executable,'-B',P.parent/'apple-toggle-keyboard-focus-v4-runtime-analysis/analyze.py','--check'])
for name,expected in [('transport-controls',16),('transport-adversarial',35)]:
 c=command('exact-reused-'+name,[P/'host-tools'/name]);j=json.loads(c['stdout']);assert expected in j.values()
# Independent byte comparison of the reuse inventory and actual V5-to-V6 delta.
reuse=json.loads((P/'immutable-reuse.json').read_bytes());copied={}
for name,old in reuse['exactCopySources'].items():
 assert sha(ROOT/name)==sha(ROOT/old);copied[name]={'source':old,'sha256':sha(ROOT/name)}
for group in ['copiedFiles','previousBindings']:
 assert all(sha(ROOT/n)==d for n,d in reuse[group].items())
prior=P.parent/'apple-toggle-keyboard-focus-v5-preparation'
deltas={}
for name in ['settings_telemetry.py','run.py','replay.py']:
 text=''.join(difflib.unified_diff((prior/name).read_text().splitlines(keepends=True),(P/name).read_text().splitlines(keepends=True),fromfile='v5/'+name,tofile='v6/'+name));deltas[name]=text
assert ''.join(deltas.values())==(P/'production-source-delta.diff').read_text()
(HERE/'independent-production-source-delta.diff').write_text(''.join(deltas.values()))
old=ast.parse((P.parent/'apple-toggle-keyboard-focus-v5-independent-review/test_review.py').read_text());new=ast.parse((P/'test_v5_independent26.py').read_text())
def methods(tree):
 c=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='IndependentV5Tests')
 return {n.name:ast.dump(n,include_attributes=False) for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
a,b=methods(old),methods(new);changed=[n for n in a if a[n]!=b[n]]
assert len(a)==len(b)==26 and changed==['test_CONTRACT_destination_captured_before_tap_return_cannot_complete']
assert before=={n:sha(ROOT/n) for n in bindings}
assert all(sha(ROOT/n)==d for n,d in priorbindings.items())
scratch=HERE/'.scratch';remaining=list(scratch.iterdir()) if scratch.exists() else []
assert not remaining,'Owned test scratch not empty: '+str(remaining)
if scratch.exists():scratch.rmdir()
record={'schema':'mixer.apple-toggle.keyboard-v6-independent-host-review-attempt.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(HERE/'run_review.py')],'pythonVersion':sys.version,'hostVersion':platform.platform(),'sourceRevisionContext':json.loads((P/'runner-binary-receipt.json').read_bytes())['sourceRevisionContext'],'currentGitRevisionQueried':False,'producerPacketSHA256':sha(seal),'rootSelectionSHA256':sha(selection),'producerFilesVerifiedBeforeAndAfter':184,'v5IndependentReviewUnchanged':True,'commands':commands,'exactCopySourcesVerified':copied,'changedIndependentV5Method':changed,'unchangedIndependentV5Methods':25,'sourceFiles':{str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):sha(p) for p in [HERE/'run_review.py',HERE/'run_host_group.py',HERE/'test_fresh.py',HERE/'test-fresh-attempt-1.py',ROOT/'AGENTS.md',ROOT/'mixer-product-plan.md',ROOT/'PLAN.md',P/'settings_telemetry.py',P/'run.py',P/'replay.py',compiler]},'allExpectedOutcomesMatched':all(c['expectedOutcomeMatched'] for c in commands),'producerPositiveMethodsRerun':sum(c['testsRun'] or 0 for c in commands if c['name'].startswith('producer-')),'freshMethodsRun':10,'scratchRemoved':True,'compiled':False,'nativeExecuted':False,'nativeInstancesQueried':False,'applicationCasesExecuted':0,'keyboardAccepted':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred'}
(HERE/'attempt-2.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':'complete','allExpectedOutcomesMatched':record['allExpectedOutcomesMatched'],'producerPositiveMethodsRerun':record['producerPositiveMethodsRerun'],'scratchRemoved':True}))
raise SystemExit(0 if record['allExpectedOutcomesMatched'] else 1)
