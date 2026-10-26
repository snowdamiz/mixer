from runner import HERE,run,identity
import shutil,json
consumer=HERE/'scratch/consumer-debug'
source=HERE/'IndependentJavaReturnTests.swift'
shutil.copyfile(source,consumer/'Platforms/Android/Tests/AppAndroidTests'/source.name)
run('copied-swift-accepts-actual-java-event',['/usr/bin/swift','test','--package-path',consumer/'Platforms/Android','--scratch-path',HERE/'scratch/consumer-build','--filter','IndependentJavaReturnTests','-j','4'],env={'MIXER_REVIEW_JAVA_EVENT':str(HERE/'java-output/full-event.json')},timeout=120)
(HERE/'fresh-consumer-final-source-binding.json').write_text(json.dumps({str(p.relative_to(consumer)):identity(p.read_bytes()) for folder in ['Generated','Sources','Platforms/Android/Sources','Platforms/Android/Tests'] for p in (consumer/folder).rglob('*') if p.is_file() and '.build' not in p.parts},indent=2)+'\n')
