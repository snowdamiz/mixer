#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,sys,tempfile,shutil
D=Path(__file__).resolve().parent;B=D/'runs/B-4';H=D/'candidate/native/android/tests/run-private-owner-host.py';spec=importlib.util.spec_from_file_location('host_support',H);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
E=D/'runs/original-pc-c16';E.mkdir(exist_ok=False);env=dict(os.environ)
for k in m.STRIP:env.pop(k,None)
S=Path(tempfile.mkdtemp(prefix='owned-original-control-',dir=E));env['TMPDIR']=str(S);runner=m.BoundedRun(E,D,env);status='failed'
try:
 classes=B/'classes';mapping=json.loads((B/'class-map.json').read_text());actual={str(p.relative_to(classes)):m.ident(p.read_bytes()) for p in sorted(classes.rglob('*.class'))};assert actual==mapping
 original=B/'inputs/native/android/tests/NativeEditorPreservationHostControls/IndependentPreservationCompletionControls.java';accepted=D.parents[1]/'verification/android-editor-preservation-membership-correction/tests/IndependentPreservationCompletionControls.java';assert original.read_bytes()==accepted.read_bytes()
 m.save(E/'binding.json',{'class_map':m.ident((B/'class-map.json').read_bytes()),'complete_classes_verified':actual,'source_map':m.ident((B/'source-map.json').read_bytes()),'unchanged_original_control':m.ident(original.read_bytes()),'runner':m.ident(H.read_bytes()),'argv':sys.argv})
 java=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin/java');runner.run('java-version',[java,'-version']);runner.run('unchanged-original-PC-C16',[java,'-Djava.io.tmpdir='+str(S),'-ea','-Xmx256m','-cp',classes,'dev.mixer.android.IndependentPreservationCompletionControls','journal-membership',B/'inputs/descriptor.json'],contains=b'PASS independent prospective preservation control journal-membership')
 status='passed-unchanged-original-PC-C16-host-only';print('PASS original PC-C16 against final B-4 exact classes')
finally:
 shutil.rmtree(S);m.save(E/'receipt.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'scope':'unchanged original authored hostile PC-C16 control; mechanical JVM only','cleanup':{'owned_scratch_removed':not S.exists(),'children_reaped':runner.reap_group(),'native_or_capture_started_or_queried':False}})
