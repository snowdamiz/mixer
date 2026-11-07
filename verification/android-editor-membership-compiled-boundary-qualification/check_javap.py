#!/usr/bin/env python3
"""Independent platform disassembler cross-check of every emitted product invocation."""
from pathlib import Path
import json,re,subprocess,sys,time,hashlib,os
D=Path(__file__).resolve().parent
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');env=dict(os.environ)
for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(k,None)
def identity(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
receipts=[]
for label,mode in [('host','host-2'),('sdk','cross-1')]:
 inv=json.loads((D/(label+'-class-inventory.json')).read_bytes());names=[c['class'].replace('/','.') for c in inv['classes']];argv=[str(jdk/'bin/javap'),'-p','-c','-s','-l','-classpath',str(D/'runs'/mode/'classes'),*names];out=D/('javap-full-'+label+'.stdout');err=D/('javap-full-'+label+'.stderr');start=time.monotonic()
 with out.open('wb') as o,err.open('wb') as e:result=subprocess.run(argv,stdout=o,stderr=e,env=env,timeout=60,check=False)
 assert result.returncode==0
 blocks=re.split(r'(?m)^Compiled from ',out.read_text())[1:];assert len(blocks)==len(inv['classes']),(len(blocks),len(inv['classes']))
 checked=0
 for c,b in zip(inv['classes'],blocks):
  actual=[];desc=None
  for line in b.splitlines():
   m=re.match(r'\s+descriptor: (\S+)',line)
   if m:desc=m.group(1)
   m=re.match(r'\s+(\d+):\s+(invokevirtual|invokespecial|invokestatic|invokeinterface|invokedynamic)\b',line)
   if m:actual.append((desc,int(m.group(1)),m.group(2)))
  expected=[(m['descriptor'],i['bci'],i['mnemonic']) for m in c['methods'] for i in m['instructions'] if 0xb6<=i['opcode']<=0xba];assert actual==expected,(c['class'],actual[:5],expected[:5]);checked+=len(actual)
 receipts.append({'mode':mode,'argv':argv,'exit':result.returncode,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':60,'reaped':True,'classes_checked':len(blocks),'exact_descriptor_bci_opcode_tuples':checked,'stdout':identity(out),'stderr':identity(err),'classfile_parser_matches_platform_disassembler':True})
 print(label,len(blocks),'classes',checked,'invocations match',flush=True)
(D/'javap-independent-check.json').write_text(json.dumps(receipts,indent=2)+'\n')
