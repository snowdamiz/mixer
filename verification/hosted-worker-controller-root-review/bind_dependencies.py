"""Compare the recorded development dependency inventory with the exact lockfile."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "hosted-worker-controller"
inventory_path = CONTROLLER / "THIRD_PARTY.yml"
lock_path = CONTROLLER / "package-lock.json"
inventory = json.loads(inventory_path.read_bytes())
lock = json.loads(lock_path.read_bytes())
packages = {key: value for key, value in lock["packages"].items() if key}
assert {row["lockPath"] for row in inventory["packages"]} == set(packages)
for row in inventory["packages"]:
    locked = packages[row["lockPath"]]
    for field in ["version", "resolved", "integrity"]:
        assert row[field] == locked[field], (row["name"], field)
    assert row["license"] and row["purpose"] and row["installScriptsExecuted"] is False
assert inventory["runtimeProductionDependencies"] == []
result = {
    "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
    "verifierSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "scope": "Root data-only locked development dependency inventory binding; no production or candidate acceptance.",
    "lockedPackages": len(inventory["packages"]), "installScriptsExecuted": 0,
    "runtimeProductionDependencies": 0,
    "inventorySHA256": hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
    "lockfileSHA256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
    "licensesPurposesVersionsURLsIntegrityPresent": True,
}
Path(__file__).with_name("dependency-binding.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"lockedPackages": result["lockedPackages"], "binding": "verified"}))
