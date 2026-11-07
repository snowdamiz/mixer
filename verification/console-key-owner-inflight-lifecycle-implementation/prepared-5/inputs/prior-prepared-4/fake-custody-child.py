"""Bounded control child. Never used by the real runtime plan."""
from pathlib import Path
import os
import sys
import time

mode, marker = sys.argv[1:]
Path(marker).write_text(str(os.getpid()))
print("owned-fake-child", flush=True)
time.sleep(2 if mode == "timeout" else 0.03)
