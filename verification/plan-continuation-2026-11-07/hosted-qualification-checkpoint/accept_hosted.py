"""Bind the completed independent hosted review without executing product code."""
import datetime
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent.parent


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


review = BASE / "generated-java-hosted-actual-review"
seal = json.loads((review / "seal.json").read_text())
for name, expected in seal["files"].items():
    require(identity(review / name) == expected, "review member changed: " + name)
result = json.loads((review / "result.json").read_text())
require(result["verdict"] == "ACCEPT" and not result["blocking_findings"], "review refusal")
acquisition = json.loads((BASE / "ci25-generated-java-actual/acquisition.json").read_text())
require(result["archive"] == {k: acquisition["archive"][k] for k in ("bytes", "sha256")}, "archive binding")
require(identity(Path(acquisition["archive"]["path"])) == result["archive"], "archive changed")
require(result["reviewed_revision"] == "25ac442c5213326b3601456a5fd62898f152111f", "revision")
require((result["run"], result["attempt"], result["job"], result["artifact"]) ==
        (42429965271, 1, 128576481908, 13596648929), "provider identity")
jobs = json.loads((BASE / "ci25-generated-java-actual/jobs.json").read_text())["jobs"]
job = next(j for j in jobs if j["id"] == result["job"])
require(job["status"] == "completed" and job["conclusion"] == "success", "job incomplete")
receipt = {
    "schema": 1,
    "acceptedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "decision": "ACCEPT_FROZEN_PAIR8_HOSTED_JAVA_BOOTSTRAP",
    "revision": result["reviewed_revision"],
    "run": result["run"], "attempt": result["attempt"],
    "job": result["job"], "artifact": result["artifact"],
    "archive": result["archive"],
    "review": str((review / "REVIEW.md").relative_to(ROOT)),
    "reviewResult": identity(review / "result.json"),
    "reviewSeal": identity(review / "seal.json"),
    "allReviewMembersMatch": True,
    "sourceCount": result["source_count"], "sourceDigest": result["source_digest"],
    "bootstrapCommands": result["bootstrap_commands"],
    "integrationCommands": result["integration_commands"],
    "consumers": result["consumers"], "javaSourcesEach": result["java_sources_per_consumer"],
    "classesEach": result["classfiles_per_consumer"],
    "memberReferencesEach": result["constant_pool_member_references_per_consumer"],
    "tamperInvocations": result["tamper_invocations"],
    "policyControls": result["policy_controls"],
    "independentChecks": result["checks"],
    "limitations": result["limitations"],
    "currentPair9QualifiedByThisReceipt": False,
    "nativeAPIFloorAPKDeviceSigningFieldLogGAQualified": False,
    "historicalFailuresAndSpecificHoldsPreserved": True,
}
destination = BASE / "generated-java-hosted-acceptance.json"
with destination.open("x") as stream:
    stream.write(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"decision": receipt["decision"], "reviewMembers": len(seal["files"]),
                  "receipt": str(destination.relative_to(ROOT))}))
