import sys,subprocess,socket
from pathlib import Path
def forbidden(*args,**kwargs):raise AssertionError('Native command/service attempted by host-only composition import')
subprocess.Popen=forbidden
socket.socket.bind=forbidden
socket.socket.connect=forbidden
sys.path.insert(0,sys.argv[1])
import composition
assert composition.h.SCOPES['interaction']['methods']==['test000PublicSettingsFullKeyboardAccess','test010ReferenceFirstTab']
assert composition.h.SCOPES['interaction']['cases']=={'keyboard-enabled-off'}
assert set(composition.h.packet.CONFIGS)=={'diagnostic'}
assert composition.h.verify()['nativeAcceptanceGranted'] is False
assert composition.join_support._ROOT['runID']=='11111111-1111-4111-8111-111111111111'
print('PASS: complete frozen source composition and compiled products; native command and socket boundaries forbidden')
