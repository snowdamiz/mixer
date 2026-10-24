#!/usr/bin/env python3
"""Run actual policy/path code on macOS; not a native iOS input receipt."""
import pathlib,subprocess,json,datetime
PACKET=pathlib.Path(__file__).resolve().parent
SOURCE=PACKET/'source'
BUILD=PACKET/'build/host-policy';BUILD.mkdir(parents=True,exist_ok=True)
commands=[]
def run(args):
 r=subprocess.run(list(map(str,args)),text=True,capture_output=True)
 commands.append(dict(argv=list(map(str,args)),exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 (PACKET/'policy-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
run(['xcrun','swiftc','--version'])
for module,libs in [('MixerCore',[]),('MixerUI',['MixerCore'])]:
 run(['xcrun','swiftc','-swift-version','6','-emit-library','-emit-module','-module-name',module,'-emit-module-path',BUILD/(module+'.swiftmodule'),'-o',BUILD/('lib'+module+'.dylib'),'-I',BUILD,'-L',BUILD]+sorted((SOURCE/'sdk/Sources'/module).glob('*.swift'))+['-l'+x for x in libs]+['-Xlinker','-install_name','-Xlinker',BUILD/('lib'+module+'.dylib')])
run(['xcrun','swiftc','-swift-version','6','-parse-as-library',PACKET/'policy-probe.swift',SOURCE/'Prototype/TogglePanPolicy.swift',SOURCE/'Prototype/AppearanceNativePathsV2.swift','-I',BUILD,'-L',BUILD,'-lMixerCore','-lMixerUI','-o',BUILD/'policy-probe'])
result=run([BUILD/'policy-probe']);(PACKET/'policy-result.json').write_text(result)
print(result)
