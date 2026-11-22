from pathlib import Path
import hashlib
import json
import os
import secrets
import shutil
import sys
import tempfile

fixture = Path(__file__).resolve().parent
root = fixture.parents[3]
if len(sys.argv) != 2:
    raise SystemExit(f"Usage: {sys.argv[0]} EMPTY_OUTPUT_DIR")
dest = Path(sys.argv[1]).resolve(strict=True)
if not dest.is_dir() or any(dest.iterdir()):
    raise SystemExit("Use an empty output directory for the disposable IME APK and receipt")
sys.path.insert(0, str(root/'vm/verification/standards-replay'))
from commands import Commands
android = Path('/opt/homebrew/share/android-commandlinetools')
tools = android/'build-tools/36.0.0'
jdk = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
jar = android/'platforms/android-36/android.jar'
scratch = Path(tempfile.mkdtemp(prefix='fieldlog-f06-ime-fixture.', dir='/private/tmp'))
password = 'F06_DISPOSABLE_IME_SIGN_PASSWORD'
env = os.environ | {'JAVA_HOME':str(jdk), password:secrets.token_hex(24)}
commands = Commands(scratch,env)
report = {'status':'failed'}
try:
    xml = scratch/'res/xml'
    xml.mkdir(parents=True)
    (xml/'input_method.xml').write_text('<input-method xmlns:android="http://schemas.android.com/apk/res/android"/>\n')
    manifest = scratch/'AndroidManifest.xml'
    manifest.write_text('''<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="dev.mixer.fixture.f06ime">
  <application android:label="Disposable F06 title IME">
    <service android:name=".TitleCommitIme" android:permission="android.permission.BIND_INPUT_METHOD"
        android:exported="true">
      <intent-filter><action android:name="android.view.InputMethod"/></intent-filter>
      <meta-data android:name="android.view.im" android:resource="@xml/input_method"/>
    </service>
  </application>
</manifest>
''')
    flats = scratch/'resources.zip'
    commands.run('compile-ime-resources',[tools/'aapt2','compile','--dir',scratch/'res','-o',flats])
    raw = scratch/'raw.apk'
    commands.run('link-ime-manifest',[tools/'aapt2','link','-I',jar,'--manifest',manifest,'--min-sdk-version','36',
                 '--target-sdk-version','36','-o',raw,flats])
    classes=scratch/'classes'
    classes.mkdir()
    source=fixture/'TitleCommitIme.java'
    commands.run('compile-ime-java',[jdk/'bin/javac','--release','17','-Xlint:all,-options','-Werror','-classpath',jar,'-d',classes,source])
    classjar=scratch/'class.jar'
    commands.run('jar-ime',[jdk/'bin/jar','--create','--file',classjar,'-C',classes,'.'])
    commands.run('dex-ime',[tools/'d8','--min-api','36','--lib',jar,'--output',scratch,classjar])
    from zipfile import ZipFile
    with ZipFile(raw,'a') as z:
        z.write(scratch/'classes.dex','classes.dex')
    aligned=scratch/'aligned.apk'
    commands.run('align-ime',[tools/'zipalign','-f','4',raw,aligned])
    key=scratch/'signer.p12'
    commands.run('local-disposable-ime-key',[jdk/'bin/keytool','-genkeypair','-noprompt','-storetype','PKCS12',
                 '-keystore',key,'-alias','test','-keyalg','EC','-groupname','secp256r1','-validity','2',
                 '-dname','CN=Disposable F06 IME','-storepass:env',password,'-keypass:env',password])
    apk=dest/'f06-commit-ime.apk'
    commands.run('sign-local-ime',[tools/'apksigner','sign','--ks',key,'--ks-key-alias','test','--ks-pass','env:'+password,
                 '--out',apk,aligned])
    key.unlink()
    verified=commands.run('verify-ime-apk',[tools/'apksigner','verify','--verbose',apk])
    assert b'v3 scheme (APK Signature Scheme v3): true' in verified
    report.update(status='passed',apkSHA256=hashlib.sha256(apk.read_bytes()).hexdigest(),
                  sourceSHA256=hashlib.sha256(source.read_bytes()).hexdigest(),devKeyRemoved=not key.exists())
finally:
    shutil.rmtree(scratch)
    report.update(scratchRemoved=not scratch.exists(),terminalCommands=len(commands.rows))
    (dest/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
