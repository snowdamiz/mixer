import hashlib, json, re
from pathlib import Path
out=Path(__file__).resolve().parent
c=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-7764d3ec')
e=c/'verification/plan-continuation-2026-11-07/android-motion-thread-fix-r2'
text=(out/'javap-NativeEnvironmentV2ObserverHostTests.stdout').read_text()
start=text.index('  private static void producerPublication();')
body=text[start:text.index('  private static void motionThreads()',start)]
invokes=[s.strip() for s in body.splitlines() if re.match(r'\s*\d+: invoke',s)]
observations=[s for s in invokes if any(k in s for k in ['getOpaque','drain:','getDurationScale','capture:','current:','setOpaque','join:','isAlive:'])]
assert body.index('Handler.drain:')<body.index('ValueAnimator.getDurationScale:')<body.index('Thread.join:')
assert 'monitorenter' not in body and 'CountDownLatch' not in body
probe=(out/'javap-ObserverHostProbe.stdout').read_text()
field=probe[probe.index('  public static float animator;'):].split('\n\n',1)[0]
assert 'ACC_VOLATILE' not in field
assert 'monitorenter' not in (out/'javap-NativeEnvironmentPlatformV2$Api33.stdout').read_text()
commands=json.loads((e/'instrumentation/commands.json').read_text())
dex=next(x for x in commands if x.get('name')=='d8')
compile_=next(x for x in commands if x.get('name')=='compile')
assert dex['argv'][dex['argv'].index('--min-api')+1]=='28'
assert compile_['argv'][compile_['argv'].index('--release')+1]=='17'
assert '/platforms/android-37.0/android.jar' in ' '.join(compile_['argv'])
result={'producerMethodObservationAndCleanupCalls':observations,'plainGetterField':field,'getterObservedBeforeJoin':True,'noMonitorInProducerOrAdapter':True,'compileSourceMapFiles':23,'sdk':37,'javaRelease':17,'dexMinimum':28,'officialContracts':[{'url':'https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/atomic/AtomicBoolean.html#getAndSet(boolean)','use':'AtomicBoolean delegates getAndSet memory semantics to VarHandle.'},{'url':'https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/invoke/VarHandle.html#getAndSet(java.lang.Object...)','use':'getAndSet has volatile read/write effects; opaque access does not publish other variables.'}],'limitations':'Compiled-code evidence and host execution; no reproduced R1 stale read, exhaustive JMM verification, or ART runtime qualification.'}
(out/'compiled-publication-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS compiled getter observations precede join; plain getter; SDK37 Java17/D8 min28 commands')
