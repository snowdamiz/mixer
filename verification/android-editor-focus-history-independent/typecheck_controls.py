#!/usr/bin/env python3
"""Typecheck only; future hooks are intentionally unresolved reflective contracts."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,datetime
D=Path(__file__).resolve().parent
J=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin/javac')
CP=D.parent/'android-editor-replacement-independent/actual-review/frozen/runs/host-1/classes'
run=D/('typecheck-'+(sys.argv[1] if len(sys.argv)>1 else '2'));run.mkdir(exist_ok=False)
empty=run/'empty-source';empty.mkdir();classes=run/'classes';classes.mkdir()
(run/'FocusHistoryControls.java').write_bytes((D/'FocusHistoryControls.java').read_bytes())
argv=[str(p) for p in [J,'--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',CP,'-d',classes,*sorted((D/'foundation').glob('*.java')),run/'FocusHistoryControls.java']]
env={key:value for key,value in os.environ.items() if key not in {'JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH','JAVA_OPTIONS'}}
child=subprocess.Popen(argv,cwd=D,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:out,err=child.communicate(timeout=60)
except BaseException:
    child.kill();out,err=child.communicate();raise
finally:empty.rmdir()
(run/'compile.stdout').write_bytes(out);(run/'compile.stderr').write_bytes(err)
receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'exit_code':child.returncode,'reaped':child.poll() is not None,'timeout_seconds':60,'control_source_sha256':hashlib.sha256((run/'FocusHistoryControls.java').read_bytes()).hexdigest(),'product_methods_or_constructors_invoked':0,'active_correction_reads':0,'scope':'javac control compilation only against pinned prior immutable host classes; no product execution','cleanup':{'child_reaped':child.poll() is not None,'empty_source_removed':not empty.exists()}}
(run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'exit':child.returncode,'reaped':child.poll() is not None,'product_executions':0}));sys.exit(child.returncode)
