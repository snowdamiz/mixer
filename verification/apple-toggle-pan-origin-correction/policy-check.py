#!/usr/bin/env python3
"""Run actual policy/path code on macOS; not a native iOS input receipt."""
import pathlib,subprocess,json,datetime,os,hashlib
os.environ["DEVELOPER_DIR"]="/Applications/Xcode_26.6.app/Contents/Developer"
PACKET=pathlib.Path(__file__).resolve().parent
SOURCE=PACKET/'app/source'
BUILD=PACKET/'build/host-policy';BUILD.mkdir(parents=True,exist_ok=True)
attempt=len(list(PACKET.glob("policy-commands-attempt-*.json")))+1
if (PACKET/"policy-commands.json").exists(): (PACKET/"policy-commands.json").rename(PACKET/f"policy-commands-attempt-{attempt}.json")
sources={str(p.relative_to(PACKET)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SOURCE.rglob("*")) if p.is_file()}
sources["policy-probe.swift"]=hashlib.sha256((PACKET/"policy-probe.swift").read_bytes()).hexdigest()
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
run(['xcrun','swiftc','-swift-version','6','-parse-as-library',PACKET/'policy-probe.swift',SOURCE/'Prototype/TogglePanPolicy.swift',SOURCE/'Prototype/TogglePanAdmission.swift',SOURCE/'Prototype/AppearanceNativePathsV2.swift','-I',BUILD,'-L',BUILD,'-lMixerCore','-lMixerUI','-o',BUILD/'policy-probe'])
result=run([BUILD/'policy-probe'])
for name,digest in sources.items():
 if hashlib.sha256((PACKET/name).read_bytes()).hexdigest()!=digest:raise RuntimeError("Source changed during host policy verification")
(PACKET/'policy-result.json').write_text(result)
(PACKET/'policy-receipt.json').write_text(json.dumps(dict(passed=True,sourceFiles=sources,sourceTreeSHA256=hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(",",":")).encode()).hexdigest(),commands="policy-commands.json",result="policy-result.json",scope="macOS executable policy/lifecycle controls only; no native UIKit run"),indent=2)+"\n")
print(result)
