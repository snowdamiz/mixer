"""Run only stdlib decision controls; deny every child, shell and socket action."""
import contextlib
import hashlib
import json
from pathlib import Path
import platform
import runpy
import sys
import time
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
start = time.monotonic()
code = 0
with (OUT / "pure-controls.stdout").open("x") as stdout, (OUT / "pure-controls.stderr").open("x") as stderr, \
        contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
    sys.argv = [str(ROOT / "hosted/scripts/test_identity_network_collector.py")]
    with mock.patch("subprocess.Popen", side_effect=AssertionError("child forbidden")), \
            mock.patch("os.system", side_effect=AssertionError("shell forbidden")), \
            mock.patch("socket.socket", side_effect=AssertionError("socket forbidden")), \
            mock.patch("socket.create_connection", side_effect=AssertionError("connection forbidden")):
        try:
            runpy.run_path(sys.argv[0], run_name="__main__")
        except SystemExit as error:
            code = error.code or 0

receipt = {"schema": 1, "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
           "tested_command": ["python3", "-B", "hosted/scripts/test_identity_network_collector.py"],
           "python": platform.python_version(), "elapsed_seconds": time.monotonic() - start,
           "exit": code, "children_and_sockets_denied": True,
           "runtime_compiler_native_or_custody_actions": False,
           "files": {path: {"bytes": len((ROOT / path).read_bytes()), "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
                     for path in ("hosted/scripts/test-identity-network.py", "hosted/scripts/test_identity_network_collector.py")}}
with (OUT / "pure-controls.json").open("x") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
print(json.dumps(receipt))
print((OUT / "pure-controls.stderr").read_text()[-2500:])
sys.exit(code)
