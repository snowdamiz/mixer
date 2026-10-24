"""Record read-only live producer and frozen-review replays before final sealing."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
source = ROOT / "attempt-1/source"
spec = importlib.util.spec_from_file_location("owned_final_replay", source / "owned_process.py")
owned = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owned)
verify_spec = importlib.util.spec_from_file_location("review_verify", ROOT / "verify.py")
review_verify = importlib.util.module_from_spec(verify_spec)
verify_spec.loader.exec_module(review_verify)
out = ROOT / "final-replay"
out.mkdir()
receipt = {"schema": 1, "status": "running", "startedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "commands": []}
commands = [
    [sys.executable, "-B", str(source / "audit_packet.py"), str(REPO)],
    [sys.executable, "-B", str(REPO / "verification/stripe-webhook-signature/verify.py")],
    [sys.executable, "-B", str(source / "audit_packet.py"), str(source / "producer")],
    [sys.executable, "-B", "-c", "import importlib.util; from pathlib import Path; p=Path('verification/stripe-webhook-signature-review/verify.py'); s=importlib.util.spec_from_file_location('v',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.verify_attempt(p.parent/'attempt-1'); print('PASS: independent attempt seal, all source inputs, command outputs and process cleanup')"],
]
try:
    for argv in commands:
        result = owned.execute(argv, cwd=REPO, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=45)
        log = out / f"command-{len(receipt['commands'])+1:02}.log"
        log.write_bytes(result.stdout)
        receipt["commands"].append({"argv": argv, "cwd": str(REPO), "exitCode": result.returncode,
                                    "timedOut": result.timedOut, "timeoutSeconds": 45, "cleanup": result.groupCleanup,
                                    "output": {"path": log.name, "bytes": log.stat().st_size,
                                               "sha256": hashlib.sha256(log.read_bytes()).hexdigest()}})
        assert result.returncode == 0 and result.groupCleanup["after"] == [], log
    receipt["status"] = "passed-read-only-replays"
finally:
    receipt["finishedUTC"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("PASS: all four final read-only replay commands; newly owned groups empty")
