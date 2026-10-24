#!/usr/bin/env python3
"""Freeze the completed independent review and all retained outputs."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
def read(name): return json.loads((OUT/name).read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
inputs = read("input-validation.json")
state = read("state.json")
cleanup = read("cleanup.json")
linux = read("linux-execution.json")
assert cleanup["scratchRemoved"] and cleanup["sourceUnchanged"] and cleanup["scratchProductSourceUnchanged"]
assert cleanup["producerPacketUnchanged"] and cleanup["dependencySourceUnchanged"]
assert cleanup["executedIndependentTestSourceMatchesDelivered"] and not cleanup["newFixtureKeyDirectoriesRetained"]
assert linux["exitCode"] == 0 and not read("linux-cleanup.json")["containerRetained"]
assert "Result: 45 passed" in (OUT/"macos-baseline.log").read_text()
assert "Result: 12 passed" in (OUT/"macos-adversarial-final.log").read_text()
assert "Result: 58 passed" in (OUT/"linux-independent.log").read_text()
for command in state["commands"]:
    assert sha(OUT/command["output"]) == command["outputSHA256"]
    if command["label"] != "adversarial-attempt-1": assert command["exitCode"] == 0
assert all(sha(ROOT/p) == digest for p,digest in inputs["sourceFiles"].items())
bindings = {str(p.relative_to(ROOT)):sha(p) for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "receipt.json" and "__pycache__" not in p.parts}
for p in [ROOT/"docs/hosted-key-owner-independent-review.md", ROOT/"verification/hosted-key-owner-root-review/unknown-kid-scope-clarification.json"]:
    bindings[str(p.relative_to(ROOT))] = sha(p)
cases = {
    "I01": "Endpoint aliases, textual IP forms, ASCII path escapes and unsupported production port rejection",
    "I02": "Real JOSE/pure verification with isolated owner replies: one final-fence retry succeeds; second retry fails unavailable; permits released",
    "I03": "Actual owner: no-op generation replacement fences stale lease; current lease succeeds; forged permit denies; disable and versioned re-enable fence old leases",
    "I04": "Actual owner: expired tombstone plus injected clock epoch fault cannot erase identity/version history or partially install an invalid mixed candidate",
    "I05": "Foreign issuer/absent kid denies; one eligible configured background flight; 128 FIFO negative cap; hit does not renew; invalid-header, known-key and unknown-profile controls; successful replacement clears negatives",
    "I06": "Actual UDP DNS: exactly eight CNAME hops succeeds, ninth rejects, IPv4 plus forbidden mapped IPv6 rejects entire result",
    "I07": "Actual TLS: malformed chunk extensions and nonempty trailers reject through wire guard and Mint",
    "I08": "Actual TLS: Unicode/vertical/form-feed header whitespace rejects; ordinary SP/HTAB OWS succeeds",
    "I09": "Conservative Age/response-delay/Expires floor, wall reversal and malformed/duplicate/missing cache directives",
    "I10": "Actual raw TCP: registration checks public Port.info controller before use; positive activation capped1; buffer16384 restored and read back; omitted active preserves1; invalid activation closes",
    "I11": "All split points of one bounded complete HTTP response; duplicate case-insensitive Content-Length and extra data reject in isolated guard",
    "I12": "Actual raw/TLS component supervision: suspended registered TLS controller holds graceful supervisor stop beyond5100ms after worker/raw-port cleanup; resumes only after controller DOWN"
}
receipt = {
    "schema":1,"status":"independent-review-recommends-component-acceptance-root-decision-pending",
    "observedUTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "sourceRevision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
    "producerReceiptSHA256":inputs["producerReceiptSHA256"],"producerFileBindingsVerifiedBeforeAndAfter":205,
    "sourceTreeDigest":inputs["sourceTreeDigest"],"sourceFiles":inputs["sourceFiles"],
    "acceptedPureVerifierUnchanged":True,"dependencySourceFileCount":len(inputs["dependencyFiles"]),
    "dependencySourceTreeDigest":inputs["dependenciesTreeDigest"],
    "configurationAndPinnedMintBindings":"configuration-bindings.json",
    "setupCommand":["python3","verification/hosted-key-owner-independent-review/run_review.py","setup"],
    "commands":state["commands"],"linuxExecution":"linux-execution.json",
    "executionResults":{"macOSFrozenBaseline":45,"macOSAdditionalIndependentCases":12,"LinuxFrozenBaselineIncludingProductionDNS":46,"LinuxAdditionalIndependentCases":12,"LinuxSingleRunTotal":58,
        "productionCompilation":"passed on macOS","productionRelease":"built on Linux without starting","fixtureExportsAndModules":"absent in production"},
    "independentCases":cases,
    "findings":[{"id":"R01","kind":"contract-wording-conflict","resolution":"root explicit clarification; no frozen product/producer changes",
        "binding":"verification/hosted-key-owner-root-review/unknown-kid-scope-clarification.json","observation":"Foreign or malformed claims may consume bounded negative/eligible-refresh work within an explicit configured binding; always unauthenticated. Token cannot select/create profile or endpoint.","independentVerification":"I05"}],
    "unresolvedImplementationFindings":[],
    "failedAttempts":[{"output":"setup-attempt-1.json","cause":"Collector mismatch for generated dependency _build metadata; scratch removed; corrected dependency-source-only hashing"},
        {"output":"adversarial-attempt-1.log","result":"9 of11 passed","cause":"Harness used nonexistent TLSFixture.date/0 and incorrectly expected s-maxage+valid Expires to reject; corrected without product change"}],
    "cleanup":{"command":["python3","verification/hosted-key-owner-independent-review/run_review.py","cleanup"],"hostReceipt":"cleanup.json","containerReceipt":"linux-cleanup.json","sourceAndDependenciesUnchanged":True,"ownedScratchAndBuildsRemoved":True,"retainedFixtureKeyDirectories":[]},
    "limitations":[
        "Recommendation covers only this frozen component; root acceptance, Application startup, HTTP authentication, authoritative database authorization, provider/deployment operations and GA remain pending.",
        "Memory/binary/parser/mailbox samples and driver-buffer reads are not RSS, kernel-buffer, native-crypto allocation, universal memory or hard real-time limits.",
        "Infinite graceful shutdown deliberately stays unavailable while a registered TLS controller is held; forced process/container termination is outside that guarantee.",
        "Lifetime profile history is bounded16 IDs and process-local; durable historical identity/version enforcement across restart remains separate.",
        "Large close-delimited responses keep the documented one-byte-read/deadline compatibility limit.",
        "The adapter retry-count test uses controlled owner replies with real JOSE/pure verification; separate actual-owner tests check generation/disable/permit/clock fences.",
        "Clock/cooldown transitions use private timing-state injection; DNS, TLS, socket, transport deadlines and cleanup exercise real platform behavior.",
        "Malformed/foreign-claim absent-key pressure remains bounded but possible; future HTTP admission and deployment-wide quotas are not proved by this component.",
        "No external providers, native simulators/emulators, physical devices, customer messages, production publication, migration or credential changes occurred."
    ],"bindings":bindings
}
(OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({"status":receipt["status"],"sourceTreeDigest":receipt["sourceTreeDigest"],"bindings":len(bindings),"receiptSHA256":sha(OUT/"receipt.json")}))
