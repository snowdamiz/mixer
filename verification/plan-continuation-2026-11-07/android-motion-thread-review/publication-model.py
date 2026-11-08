"""Finite JMM happens-before argument; not a JVM/ART stale-read reproduction.

The actual adapter's emitted bytecode is retained in host-replay. The upstream
ValueAnimator getter reads a nonvolatile scalar in the inspected AOSP source.
This model enumerates the relevant normal-return coalesced callback path only.
"""
import json
from pathlib import Path
out=Path(__file__).resolve().parent
edges=[
 ('A.writeScale','A.casSuccess'),('A.casSuccess','A.enqueueRelease'),
 ('B.writeScale','B.phaseRead'),('B.phaseRead','B.casFailureRead'),
 ('M.dequeueAcquire','M.queuedSetFalse'),('M.queuedSetFalse','M.phaseRead'),('M.phaseRead','M.getterRead'),
 ('A.enqueueRelease','M.dequeueAcquire'),('A.casSuccess','B.casFailureRead'),
 ('M.activationWrite','B.phaseRead'),('M.activationWrite','M.phaseRead')]
def reachable(graph,source,target):
 todo=[source];seen=set()
 while todo:
  node=todo.pop()
  if node==target:return True
  if node in seen:continue
  seen.add(node);todo.extend(b for a,b in graph if a==node)
 return False
assert reachable(edges,'A.writeScale','M.getterRead')
assert not reachable(edges,'B.writeScale','M.getterRead')
# Positive control: a release write on every callback and a matching acquire
# read when draining creates the missing handoff; this does not edit product.
control=edges+[('B.casFailureRead','B.publishWrite'),('B.publishWrite','M.acquirePending'),('M.acquirePending','M.getterRead')]
assert reachable(control,'B.writeScale','M.getterRead')
result={'status':'PASS finite HB counterexample/control','coalescedPathEdges':edges,'firstUpdatePublished':True,'coalescedUpdatePublished':False,'releaseAcquireControlPublished':True,'limits':'A source/specification argument only. No stale getter was observed on JVM or Android. Other unspecified framework synchronization is not assumed. This is not a memory-model checker for all Java executions.','sources':[
 {'url':'https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/java/android/animation/ValueAnimator.java','blob':'492c2ffc561f45adf0afe32f5e2a95bb6cb43eb6','lines':'99,316-343','use':'plain scalar write/getter; source behavior is not an exact API37 image binding'},
 {'url':'https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/invoke/VarHandle.html#compareAndSet(java.lang.Object...)','use':'failed compareAndSet reads witness; conditional set does not occur'},
 {'url':'https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/atomic/AtomicBoolean.html#set(boolean)','use':'set(false) is a volatile write, not an acquire read'}]}
(out/'publication-model.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS first callback publishes; coalesced callback has no modeled HB path; explicit release/acquire control publishes. NOT a native/JVM stale-read reproduction.')
