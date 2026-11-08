"""Execute unchanged retained suite bodies, then independent boundary probes."""
import ast, hashlib, json, sys
from pathlib import Path
OWN=Path(__file__).resolve().parent
CAND=OWN.parent/'cache-refusal-cleanup-r8'
def need(value,message):
    if not value:raise RuntimeError(message)
original=(CAND/'verify_controls.py').read_text()
review=(OWN/'review.py').read_text()
need(review==original.replace('\nCAND=OWN\n','\nCAND=Path('+json.dumps(str(CAND))+')\n'),'Only candidate binding may differ')
for name in ['stdin_guard.py','focused_controls.py']:need((OWN/name).read_bytes()==(CAND/name).read_bytes(),'Copied control drift')
need(CAND.is_absolute() and OWN.is_absolute(),'Absolute fixtures required')
namespace={'__file__':str(OWN/'review.py'),'__name__':'__main__'}
retained_exit=None
try:exec(compile(review,str(OWN/'review.py'),'exec'),namespace)
except SystemExit as error:retained_exit=error.code
need(retained_exit in (0,1),'Unexpected retained suite exit')
exec(compile((OWN/'fresh_probes.py').read_bytes(),str(OWN/'fresh_probes.py'),'exec'),namespace)
sys.exit(0 if retained_exit==0 and namespace['fresh_result'].wasSuccessful() else 1)
