from runner import HERE,run,identity
from pathlib import Path
import shutil,json
scratch=HERE/'scratch';sources=scratch/'java-source';classes=scratch/'java-classes';empty=scratch/'java-empty'
sources.mkdir(exist_ok=True);classes.mkdir(exist_ok=True);empty.mkdir(exist_ok=True)
export=HERE/'scratch/consumer-debug/Generated/MixerAndroid/app/src/dev/mixer/android'
java='/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin/'
names=['Json.java','UiPacket.java','AppearanceDescriptorV2.java','AppearanceGeometryV2.java']
for name in names:shutil.copyfile(export/name,sources/name)
shutil.copyfile(HERE/'IndependentPairProbe.java',sources/'IndependentPairProbe.java')
srcs=sorted(sources.glob('*.java'))
run('independent-production-java-compile',[java+'javac','--release','17','-encoding','UTF-8','-Xlint:all','-Werror','-classpath',empty,'-sourcepath',empty,'-d',classes,*srcs],timeout=120)
output=HERE/'java-output'
run('independent-production-java-execute',[java+'java','-ea','-classpath',classes,'dev.mixer.android.IndependentPairProbe',HERE/'swift-output',output],timeout=60)
(HERE/'java-source-binding.json').write_text(json.dumps({p.name:identity(p.read_bytes()) for p in srcs},indent=2)+'\n')
(HERE/'java-class-binding.json').write_text(json.dumps({str(p.relative_to(classes)):identity(p.read_bytes()) for p in classes.rglob('*.class')},indent=2)+'\n')
(HERE/'java-output-binding.json').write_text(json.dumps({p.name:identity(p.read_bytes()) for p in output.iterdir()},indent=2)+'\n')
