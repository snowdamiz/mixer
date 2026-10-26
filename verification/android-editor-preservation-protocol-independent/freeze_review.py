"""Freeze only this independent review lane; never mutate external inputs."""
import datetime
import hashlib
import json
from pathlib import Path

own = Path(__file__).resolve().parent
assert json.loads((own / "execution-receipt.json").read_text())["success"]
assert json.loads((own / "input-custody.json").read_text())["success"]
model = json.loads((own / "commands/model.stdout").read_text())
assert model["all_passed"] and model["control_count"] == 9
members = []
for path in sorted(own.rglob("*")):
    if not path.is_file() or path.name == "review-seal.json":
        continue
    data = path.read_bytes()
    members.append({"path": str(path.relative_to(own)), "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest()})
seal = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Frozen independent preservation-completion protocol review and bounded abstract controls",
        "verdict": "changes-required-before-implementation-selection",
        "implementation_or_native_or_GA_acceptance": False,
        "member_count": len(members), "member_bytes": sum(m["bytes"] for m in members),
        "members": members}
path = own / "review-seal.json"
path.write_text(json.dumps(seal, indent=2) + "\n")
print(json.dumps({"review_seal_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                  "member_count": seal["member_count"], "member_bytes": seal["member_bytes"]}))
