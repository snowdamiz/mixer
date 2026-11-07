import json
from pathlib import Path
import signal
import subprocess
import sys
from unittest.mock import patch
from cleanup_control import stop

out = Path(__file__).resolve().parent
rows = []
for script in ['pass', 'import time; time.sleep(60)']:
    p = subprocess.Popen([sys.executable, '-c', script], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if script == 'pass': p.wait(timeout=5)
    result = stop(p)
    assert result['groupAbsent'] and result['leaderReaped'], result
    rows.append(result)
class Completed:
    pid = 900001
    returncode = 0
    def poll(self): return 0
with patch('cleanup_control.os.killpg', side_effect=PermissionError('simulated absent group')), patch('cleanup_control.subprocess.run', return_value=subprocess.CompletedProcess([],1,'','')):
    result = stop(Completed()); assert result['groupAbsent'] and not result['signals'];rows.append(result)
with patch('cleanup_control.os.killpg', side_effect=PermissionError('simulated inaccessible group')), patch('cleanup_control.subprocess.run', return_value=subprocess.CompletedProcess([],0,'900001\n','')):
    result = stop(Completed()); assert not result['groupAbsent'] and 'signalError' in result;rows.append(result)
with patch('cleanup_control.os.killpg', side_effect=PermissionError('simulated uncertain group')), patch('cleanup_control.subprocess.run', return_value=subprocess.CompletedProcess([],2,'','error')):
    result = stop(Completed()); assert not result['groupAbsent'] and not result['signals'];rows.append(result)
(out/'cleanup-control.json').write_text(json.dumps({'status':'passed','controls':rows,'scope':'two fresh owned process groups plus three mocked PermissionError outcomes; no historical process probes'},indent=2)+'\n')
print('PASS cleanup control: exited/live owned groups and PermissionError absent/present/unknown')
