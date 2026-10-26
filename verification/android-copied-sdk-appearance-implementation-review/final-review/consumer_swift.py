from runner import HERE,run,identity
import shutil,json
consumer=HERE/'scratch/consumer-debug'
tests=consumer/'Platforms/Android/Tests/AppAndroidTests';source=HERE/'IndependentCopiedPairTests.swift'
shutil.copyfile(source,tests/source.name)
output=HERE/'swift-output';output.mkdir(exist_ok=True)
env={'MIXER_REVIEW_OUTPUT':str(output),'MIXER_REVIEW_ASSET':str(consumer/'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json')}
# run('fresh-copied-generated-tests',['/usr/bin/swift','test','--package-path',consumer/'Platforms/Android','--scratch-path',HERE/'scratch/consumer-build','--filter','ApplicationSessionTests','-j','4'],env=env,timeout=240)
run('fresh-copied-independent-tests-corrected-status',['/usr/bin/swift','test','--package-path',consumer/'Platforms/Android','--scratch-path',HERE/'scratch/consumer-build','--filter','IndependentCopiedPairTests','-j','4'],env=env,timeout=180)
run('fresh-copied-dependency-paths',['/usr/bin/swift','package','--package-path',consumer/'Platforms/Android','show-dependencies','--format','json'],timeout=60)
source_files={str(p.relative_to(consumer)):identity(p.read_bytes()) for folder in ['Generated','Sources','Platforms/Android/Sources','Platforms/Android/Tests'] for p in (consumer/folder).rglob('*') if p.is_file() and '.build' not in p.parts}
(HERE/'fresh-consumer-source-binding.json').write_text(json.dumps(source_files,indent=2)+'\n')
(HERE/'swift-output-binding.json').write_text(json.dumps({p.name:identity(p.read_bytes()) for p in output.iterdir()},indent=2)+'\n')
