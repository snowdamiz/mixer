"""Configure a private copy of the XCTest plan with the current loopback lease."""
import json
from pathlib import Path
import plistlib
import re
import sys
import time

kit, control, output = (Path(arg).resolve() for arg in sys.argv[1:])
plan_path, = kit.glob("F11NativeWitness_*.xctestrun")
plan = plistlib.loads(plan_path.read_bytes())
lease = json.loads(control.read_bytes())
assert 1023 < lease["port"] < 65536 and re.fullmatch(r"[A-Za-z0-9_-]{43}", lease["token"])
roots = json.loads((kit / "releases/roots.json").read_bytes())
assert time.time() < roots[0]["not_after_unix"], "F11 development trust expired"
assert output.parent == kit and not output.exists(), "Place the private .xctestrun beside the products"
target = plan["F11NativeWitnessUITests"]
target.setdefault("EnvironmentVariables", {}).update(
    F11_CONTROL_PORT=str(lease["port"]), F11_CONTROL_TOKEN=lease["token"])
target["OnlyTestIdentifiers"] = ["F11WitnessUITests/testPasteSaveAndCommitRestoredNote"]
target["TestTimeoutsEnabled"] = True
target["DefaultTestExecutionTimeAllowance"] = 235
target["MaximumTestExecutionTimeAllowance"] = 260
output.write_bytes(plistlib.dumps(plan))
output.chmod(0o600)
