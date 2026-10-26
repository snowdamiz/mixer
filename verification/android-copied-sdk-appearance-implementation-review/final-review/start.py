from pathlib import Path
import json,sys,shutil
from runner import HERE,run,identity
scratch=HERE/'scratch';scratch.mkdir(exist_ok=True)
candidate=HERE/'candidate'
run('python-version',[sys.executable,'--version'])
run('swift-version',['/usr/bin/swift','--version'])
java='/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin/'
run('java-version',[java+'java','--version']);run('javac-version',[java+'javac','--version'])
raw=candidate/'cli/Sources/MixerBuild/Resources/android-build.py'
run('raw-import',[sys.executable,'-B','-c',"import runpy;runpy.run_path("+repr(str(raw))+",run_name='independent_raw_import')"])
run('raw-official-inspect',[sys.executable,'-B',raw,'inspect'],timeout=180)
for configuration in ['debug','release']:
    exe=HERE/'executables'/('cli-'+configuration)/'mixer'
    run('actual-create-'+configuration,[exe,'create','ReviewPair','--platform','android','--directory',scratch/('consumer-'+configuration),'--sdk-path',candidate/'sdk','--android-adapter-path',candidate/'native/android'],timeout=180)
run('actual-create-ios',[HERE/'executables/cli-debug/mixer','create','ReviewIOS','--directory',scratch/'ios','--sdk-path',candidate/'sdk'],timeout=120)
summary={}
for configuration in ['debug','release']:
    consumer=scratch/('consumer-'+configuration);sdk=consumer/'Generated/MixerSDK';adapter=consumer/'Generated/MixerAndroid'
    obs=json.loads((HERE.parent/'preaccess/selected-inputs/verification/android-copied-sdk-appearance-contract/proposed-profile-observation.json').read_text())
    for part,path in [('sdk',sdk),('adapter',adapter)]:
        for rel,expected in obs[part+'_files'].items():assert identity((path/rel).read_bytes())==expected,rel
    descriptor=adapter/'app/assets/MixerAppearanceV2/descriptor.json';assert identity(descriptor.read_bytes())==obs['default_descriptor']
    driver=(adapter/'android-build.py').read_text();assert '__MIXER_ANDROID_SOURCE_PROFILE_HEX__' not in driver
    summary[configuration]={'descriptor':identity(descriptor.read_bytes()),'driver':identity(driver.encode()),'lock':json.loads((consumer/'mixer.lock').read_text())}
(HERE/'created-binding.json').write_text(json.dumps(summary,indent=2)+'\n')
