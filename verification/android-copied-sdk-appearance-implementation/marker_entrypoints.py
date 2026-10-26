import json, os, pathlib, shutil, tempfile
from run import BASE, run
REPO=BASE.parents[1]
raw=(REPO/'cli/Sources/MixerBuild/Resources/android-build.py').read_text()
marker='__MIXER_ANDROID_SOURCE_PROFILE_HEX__'
results=[]
with tempfile.TemporaryDirectory(prefix='mixer-marker-entrypoints-',dir='/tmp') as tmp:
    base=pathlib.Path(tmp); tools=base/'tools';tools.mkdir();sentinel=base/'TOOLS-RAN'
    script=tools/'swift';script.write_text('#!/bin/sh\n/usr/bin/touch "'+str(sentinel)+'"\nexit 99\n');script.chmod(0o755)
    for config in ['Debug','Release']:
        install=base/config;install.mkdir()
        shutil.copy2(REPO/'cli/.build'/config.lower()/'mixer',install/'mixer')
        shutil.copytree(REPO/'cli/.build/out/Products'/config/'MixerCLI_MixerBuild.bundle',install/'MixerCLI_MixerBuild.bundle')
        resource=install/'MixerCLI_MixerBuild.bundle/Contents/Resources/Resources/android-build.py'
        env=os.environ.copy();env['PATH']=str(tools)+os.pathsep+env['PATH'];env['PACKAGE_RESOURCE_BUNDLE_PATH']=str(install)
        for mutation in ['missing','duplicate']:
            resource.write_text(raw.replace(marker,'absent') if mutation=='missing' else raw+'\n# '+marker+'\n')
            target=base/(config+mutation)
            code,folder=run(config+'-marker-'+mutation,[str(install/'mixer'),'create','MarkerApp','--platform','android','--directory',str(target),'--sdk-path',str(REPO/'sdk'),'--android-adapter-path',str(REPO/'native/android')],20,env=env)
            output=(folder/'output.txt').read_text()
            assert code!=0 and 'android.driver-profile' in output,(code,output)
            assert not sentinel.exists() and not target.exists() and not list(base.glob('.mixer-create-*'))
            results.append({'configuration':config,'mutation':mutation,'command_result':str(folder.relative_to(BASE)),'refused_before_host_swift_or_android_inspect':True,'destination_absent':True,'staging_cleaned':True})
(BASE/'marker-entrypoint-report.json').write_text(json.dumps({'checks':results,'owned_copied_installations_removed':True},indent=2)+'\n')
