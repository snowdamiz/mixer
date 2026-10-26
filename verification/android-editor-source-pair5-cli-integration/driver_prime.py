"""Exact production-driver Swift command and cwd, as a separately bounded prime."""
import importlib.util,pathlib,subprocess
HERE=pathlib.Path(__file__).resolve().parent;root=HERE/'consumers/PairFiveConsumer'
p=root/'Generated/MixerAndroid/android-build.py'
s=importlib.util.spec_from_file_location('driver_prime',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
command=[m.SWIFT,'build','--package-path',root/'Platforms/Android','--scratch-path',root/'.mixer/android-build/swift','--swift-sdks-path',m.SWIFT_SDKS,'--swift-sdk',m.SDK_ID,'-c','release','--product','AppAndroid','-Xlinker','-z','-Xlinker','max-page-size=16384']
print('Exact command:',list(map(str,command)),'cwd:',root,flush=True)
p=subprocess.run(list(map(str,command)),cwd=root,env=m.ENV)
raise SystemExit(p.returncode)
