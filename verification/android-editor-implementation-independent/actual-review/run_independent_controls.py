#!/usr/bin/env python3
"""Bounded independent controls using only the copied, complete-source host output."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
OUT=HERE/'independent-controls-1'
OUT.mkdir(exist_ok=False)
BASE=HERE/'frozen/runs/host-1/classes'
DESCRIPTOR=HERE/'frozen/runs/host-1/inputs/descriptor.json'
CLASSES=OUT/'classes'
CLASSES.mkdir()
env=dict(os.environ)
for key in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):
    env.pop(key,None)
commands=[]


def identity(path):
    data=path.read_bytes();return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def run(label,argv):
    result=subprocess.run([str(x) for x in argv],cwd=HERE,env=env,capture_output=True,text=True,timeout=35,check=False)
    (OUT/(label+'.stdout.txt')).write_text(result.stdout)
    (OUT/(label+'.stderr.txt')).write_text(result.stderr)
    commands.append({'label':label,'argv':[str(x) for x in argv],'exit':result.returncode,
                     'stdout':identity(OUT/(label+'.stdout.txt')),'stderr':identity(OUT/(label+'.stderr.txt')),
                     'owned_child_exited':True})
    (OUT/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    print(label,'exit',result.returncode,result.stdout.strip(),flush=True)
    return result


run('javac-version',[JDK/'bin/javac','-version'])
run('java-version',[JDK/'bin/java','-version'])
compile_result=run('compile',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none',
                              '-sourcepath','','-cp',BASE,'-d',CLASSES,
                              HERE/'IndependentEditorReviewTests.java',HERE.parent/'DescriptorClosure.java'])
assert compile_result.returncode==0
classpath=str(CLASSES)+os.pathsep+str(BASE)
run('compiled-adapter-shape',[JDK/'bin/java','-ea','-cp',classpath,'DescriptorClosure',
                              'dev.mixer.android.NativeEditorConnectionV2$Api34'])
for case in ('metadata-success','metadata-failure','mutation-getter-reentry','close-roster-reentry','close-target-reentry'):
    run(case,[JDK/'bin/java','-ea','-Xmx256m','-cp',classpath,'dev.mixer.android.IndependentEditorReviewTests',case,DESCRIPTOR])
receipt={
    'schema':1,'at':datetime.datetime.now(datetime.UTC).isoformat(),'argv':sys.argv,'python':sys.version,
    'scope':'Independent actual-source extra controls on complete frozen candidate; Android/JNI leaves remain authored doubles',
    'producer_seal_sha256':'99ee53d6cf73cc062d5f39f7caa743dfed68f0f22522788adabe83159cacc9cd',
    'production_source_or_leaf_edits':False,'test_source':identity(HERE/'IndependentEditorReviewTests.java'),
    'script':identity(Path(__file__)),'commands':commands,
    'cleanup':'All exact owned finite javac/JVM children exited within 35-second bounds; no native/capture/process inventory',
    'no_native_or_GA_acceptance':True,
}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
