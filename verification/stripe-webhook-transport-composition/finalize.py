"""Finalize composition summary and explicit supplemental local cleanup check."""
import datetime
import hashlib
import json
from pathlib import Path
import shlex
import socket
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


chosen = HERE / "attempt-4"
composed = read(chosen / "receipt.json")
nested = read(chosen / "hosted/receipt.json")
assert composed["status"] == "passed-normalized-isolated-hosted-composition-root-integration-pending"
pgstart = next(c for c in nested["commands"] if c["label"] == "postgres-start")["argv"]
options = shlex.split(pgstart[pgstart.index("-o") + 1])
assert options[options.index("-h") + 1] == "127.0.0.1"
port = int(options[options.index("-p") + 1])
data = Path(pgstart[pgstart.index("-D") + 1])
try:
    connection = socket.create_connection(("127.0.0.1", port), timeout=1)
except ConnectionRefusedError:
    refused = True
else:
    connection.close()
    refused = False
assert refused and not data.exists() and not data.parent.exists()
save(HERE / "supplemental-cleanup.json", {
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())],
    "host": "127.0.0.1", "port": port, "postgresPortRefused": refused,
    "postgresDataDirectory": str(data), "postgresDataDirectoryAbsent": not data.exists(),
    "postgresScratchDirectoryAbsent": not data.parent.exists(),
    "scope": "Only the collector's previously observed loopback port and private PostgreSQL paths",
})
attempts = []
for folder in sorted(HERE.glob("attempt-*")):
    value = read(folder / "receipt.json")
    attempts.append({"attempt": folder.name, "status": value["status"], "failure": value.get("failure"), "sealSHA256": sha(folder / "seal.json")})
save(HERE / "receipt.json", {
    "schema": 1,
    "status": "normalized-private-hosted-composition-passed-root-integration-pending",
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "sourceRevision": composed["sourceRevision"],
    "acceptedAttempt": "attempt-4", "attempts": attempts,
    "producerSealSHA256": composed["producerSealSHA256"],
    "reviewSealSHA256": composed["reviewSealSHA256"],
    "reviewedCandidateSHA256": composed["normalization"]["reviewedSHA256"],
    "normalizedCandidateSHA256": composed["normalization"]["composedSHA256"],
    "sourceDigest": composed["sourceDigest"], "sourceInputs": 72,
    "fullHostedSuite": composed["fullHostedSuite"],
    "productionTransportModules": 4,
    "permanentSourceAdditions": ["hosted/lib/mixer_hosted/billing/webhook_transport.ex"],
    "permanentTestOrCollectorChanges": [],
    "proposedLaterChecks": [
        "Add the production BEAM/helper/export policy to the permanent release collector after root review.",
        "Add production-mode child-BEAM regressions for schema-filter reconstruction/drop behavior and missing-permit refusal after root review.",
    ],
    "limitations": [
        "Full hosted suite does not activate the candidate role or replay the upstream wire matrix.",
        "Early failed attempts2/3 source closures are explicitly reconstructed from original raw/baseline bytes and retained actual formatter diffs; original sealed outputs are unchanged.",
        "Two existing network-namespace fixtures are skipped on macOS and are not passes.",
        "P11/P12/P14/P15/P16, G23 and GA remain pending.",
    ],
    "liveIntegrated": False, "publicAdmissionAccepted": False, "gaAccepted": False,
    "providerContacted": False, "nativeStarted": False,
    "catalogInspectorOrAuthorityReviewRetried": False,
})
result = subprocess.run([sys.executable, "-B", str(HERE / "verify.py"), "--preseal"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(HERE / "verification.log").write_bytes(result.stdout)
assert result.returncode == 0, result.stdout.decode()
seal = {str(path.relative_to(ROOT)): {"bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(HERE.rglob("*")) if path.is_file() and path != HERE / "seal.json"}
doc = ROOT / "docs/stripe-webhook-transport-composition.md"
seal[str(doc.relative_to(ROOT))] = {"bytes": doc.stat().st_size, "sha256": sha(doc)}
save(HERE / "seal.json", seal)
print(json.dumps({"status": "frozen", "files": len(seal), "sealSHA256": sha(HERE / "seal.json")}))
