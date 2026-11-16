"""Explicit process authority: no automatic process or descriptor cleanup."""
import json
import os
import subprocess
UNKNOWN_AUTHORITIES = []
class InertPopen(subprocess.Popen):
    def __del__(self):pass
    def __enter__(self):return self
    def __exit__(self,kind,value,traceback):return False
def freeze_unknown(authority,metadata,hold_path):
    UNKNOWN_AUTHORITIES.append(authority)
    try:
        hold_path.write_text(json.dumps(metadata,indent=2,sort_keys=True)+'\n')
    finally:
        os._exit(74)
