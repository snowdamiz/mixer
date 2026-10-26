#!/usr/bin/env python3
"""Reconcile fresh8 ELF outputs with exact dependency-resolution receipts."""
import datetime,hashlib,json,pathlib,re,sys
O=pathlib.Path(__file__).resolve().parent;P=O.parent/'android-editor-source-pair5-cli-integration';H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();checks=[]
remapping={str(P/r['original']):r for r in json.loads((P/'artifact-remapping.json').read_text())['remapping']}
def ck(x,label):
 checks.append({'label':label,'passed':bool(x)})
 if not x:raise AssertionError(label)
for e in json.loads((P/'consumer-and-elf-audit.json').read_text())['elf']:
 name='libAppAndroid.so' if e['kind']=='app-owned-Swift' else 'libmixer_android_jni.so';prefix='independent-'+e['context']+'-'+e['configuration']+'-'+name
 dynamic=(O/'evidence'/(prefix+'-dynamic.log')).read_text();actual=re.findall(r'\(NEEDED\).*\[([^\]]+)\]',dynamic);ck(actual==e['needed'],'exact NEEDED '+prefix)
 symbols=(O/'evidence'/(prefix+'-symbols.log')).read_text();ck(all(s in symbols for s in e['required_symbols']),'all receipt ABI symbols '+prefix)
 for row in e['resolved']:
  if 'path' not in row:
   ck(row=={'name':row['name'],'kind':'Android-system-contract'} and row['name'] in {'libc.so','libdl.so','libm.so','liblog.so','libandroid.so'},'Android system dependency contract '+prefix+' '+row['name']);continue
  f=pathlib.Path(row['path'])
  if not f.exists():
   mapped=remapping[str(f)];ck(mapped['sha256']==row['sha256'] and mapped['bytes']==row['bytes'],'exact dependency remapping '+prefix);f=P/mapped['retained']
  ck(f.stat().st_size==row['bytes'] and H(f)==row['sha256'],'resolved dependency '+prefix+' '+row['name'])
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,*sys.argv],'python_version':sys.version,'checks':checks,'passed':all(x['passed'] for x in checks),'scope':'Exact recorded dependency resolution identities and ABI symbol set against fresh retained ELF dynamic/symbol outputs. No native library execution.'};(O/'elf-dependency-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'checks':len(checks)}))
