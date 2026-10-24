#!/usr/bin/env python3
"""New app, unchanged reviewed XCTest/owned-instance controller; root dispatch only."""
import argparse,hashlib,importlib,json,os,pathlib,signal,subprocess,sys
BASE=pathlib.Path(__file__).resolve().parent;ROOT=BASE.parents[1]
PARENT=ROOT/'verification/apple-toggle-pan-origin-correction'
sys.path.insert(0,str(PARENT))
import harness as inherited
import apps as artifact
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
require=artifact.require
original_manifest=artifact.expected_manifest

def expected_manifest(key):
 return read(BASE/'built-app-manifest.json') if key=='diagnostic' else original_manifest(key)
artifact.expected_manifest=expected_manifest

class CandidateApps:
 CONFIGS=artifact.CONFIGS
 @staticmethod
 def restore(destination,key):
  config=artifact.CONFIGS[key];manifest=expected_manifest(key)
  folder=BASE if key=='diagnostic' else artifact.ORIGINAL/config['folder']
  payload,modes=artifact.archive_payload(folder/'built-app.tar.gz',manifest,config)
  require(not destination.exists() and not destination.is_symlink() and destination.resolve()==destination,'Fresh canonical restore destination required')
  destination.mkdir(parents=True);app=destination/config['app']
  for directory in [app,app/'Frameworks',app/'_CodeSignature']:directory.mkdir(exist_ok=True);directory.chmod(0o755)
  for name,value in payload.items():
   target=app/artifact.relative_name(name);target.write_bytes(value);target.chmod(modes[name])
  return artifact.verify_restored(app,key)
 verify_installed=staticmethod(artifact.verify_installed)

def verify():
 seal=read(BASE/'packet-seal.json')
 require(seal['schema']=='mixer.apple-toggle.semantic-activation.1','Wrong semantic packet')
 for name,digest in seal['files'].items():
  p=ROOT/artifact.relative_name(name);require(p.is_file() and not p.is_symlink() and sha(p)==digest,'Sealed source changed: '+name)
 # A separate process checks the entire unchanged parent source, runner archive,
 # compiled Products, frozen comparator, historical evidence, compiler and tools.
 cmd=[sys.executable,'-B',str(PARENT/'harness.py'),'verify']
 p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=60)
 require(p.returncode==0,'Parent verifier failed: '+p.stderr)
 parent=json.loads(p.stdout);require(parent['sealSHA256']=='a12746e44aa43cd1176747a9afc637c102f736a6201ee9b8cb2580f8fefb84ba','Parent identity changed')
 selection=read(BASE/'selection.json');source=BASE/'source'
 actual={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file() and not p.is_symlink()}
 lock=read(BASE/'source-lock.json');require(actual==lock['sha256'],'Candidate source lock mismatch')
 digest=hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()).hexdigest();require(digest==lock['sourceClosureSHA256'],'Candidate closure mismatch')
 changed=sorted(k for k in set(actual)|set(selection['sourceBefore']) if actual.get(k)!=selection['sourceBefore'].get(k))
 require(changed==['Prototype/AuthoredToggleCarrier.swift','Prototype/SemanticActivationChecks.swift','Prototype/main.swift'],'Candidate escaped semantic files')
 receipt=read(BASE/'receipt.json');manifest=expected_manifest('diagnostic');commands=read(BASE/receipt['buildCommands'])
 require(receipt['sourceClosureSHA256']==digest and receipt['archiveSHA256']==manifest['archiveSHA256'],'Build receipt mismatch')
 require(all(x['exitCode']==0 for x in commands),'Candidate build failed')
 compiled={v.split('/source/',1)[1] for command in commands for v in command['argv'] if '/source/' in v and v.endswith('.swift')}
 require(compiled=={n for n in actual if n.endswith('.swift')},'Exact compile source set mismatch')
 require(all(sha(pathlib.Path(n))==d for n,d in receipt['toolFiles'].items()),'Candidate compiler/tools changed')
 payload,_=artifact.archive_payload(BASE/'built-app.tar.gz',manifest,artifact.CONFIGS['diagnostic'])
 binaries={n:artifact.frozen.macho(payload[n]) for n in [artifact.CONFIGS['diagnostic']['executable'],'Frameworks/libMixerCore.dylib','Frameworks/libMixerUI.dylib']}
 return {'sealSHA256':sha(BASE/'packet-seal.json'),'candidateSourceClosureSHA256':digest,'candidateArchiveSHA256':manifest['archiveSHA256'],'binaryBuildVersions':binaries,'parent':parent,'changedDiagnosticFiles':changed,'harnessScope':'Exact prior10interaction/2original-direct methods and strict original oracle; semantic36 rows reviewed separately','nativeExecution':False}

inherited.BASE=BASE
inherited.packet=CandidateApps
inherited.verify=verify
original_summary=inherited.runtime_summary

def summary(*args,**kwargs):
 value=original_summary(*args,**kwargs)
 value['schema']='mixer.apple-toggle.semantic-activation-runtime.1'
 value['semanticCallbackComponents']='Separate36-row raw observation review required; original direct verdict remains authoritative for original19/12 suites'
 return value
inherited.runtime_summary=summary

def main():
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['verify','run','cleanup']);parser.add_argument('--reviewed-seal');parser.add_argument('--scope',choices=['interaction','direct'],default='interaction');a=parser.parse_args()
 if a.action=='verify':print(json.dumps(verify(),sort_keys=True))
 elif a.action=='run':inherited.run(a.reviewed_seal,a.scope)
 else:
  inherited.RUN_DIR=inherited.select_runtime_directory(a.scope);life=read(inherited.RUN_DIR/'lifecycle.json');require(life['verifiedHandoff']['sealSHA256']==verify()['sealSHA256'],'Recovery identity changed');commands=inherited.Commands(inherited.RUN_DIR/'recovery-commands.json')
  results=inherited.cleanup_independently([('owned-simulator-and-baseline-reconciliation',lambda:inherited.cleanup(life,commands)),('ephemeral-capability-workspace-removal',lambda:inherited.remove_ephemeral(life))]);life.update(cleanedUp=all(v['passed'] for v in results),recoveryCleanupResults=results);inherited.write(inherited.RUN_DIR/'lifecycle.json',life);require(life['cleanedUp'],'Recovery incomplete')
if __name__=='__main__':
 def stop(signum,frame):raise KeyboardInterrupt('Root semantic harness interruption')
 signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop);main()
