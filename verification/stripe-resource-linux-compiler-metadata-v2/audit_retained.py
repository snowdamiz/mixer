"""Read-only provenance audit; no network, Docker, solver, or crypto execution."""
import hashlib
import json
from pathlib import Path

import run_container as candidate


def stanza(text):
    result, key = {}, None
    for line in text.splitlines():
        if line.startswith((" ", "\t")) and key:
            result[key] += "\n"+line
        elif ":" in line:
            key, value = line.split(":", 1)
            result[key] = value.lstrip(" ")
    return result


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    here, root = candidate.HERE, candidate.ROOT
    receipt = json.loads((here/"attempt/receipt.json").read_text())
    require(candidate.sha(candidate.SELECTION) == candidate.SELECTION_SHA, "selection changed")
    require(candidate.sha(candidate.ADDENDUM) == candidate.ADDENDUM_SHA, "addendum changed")
    require(candidate.sha(here/"run_container.py") == receipt["runnerSha256"], "executed runner changed")
    require(candidate.sha(candidate.METADATA) == candidate.METADATA_SHA, "prior seal changed")
    for name, digest in json.loads(candidate.METADATA.read_text())["files"].items():
        require(candidate.sha(root/name) == digest, "prior sealed file changed")
    for name, digest in receipt["snapshotFiles"].items():
        require(candidate.sha(here/"inputs"/name) == digest, "executed input changed")
    for command in receipt["commands"]:
        require(command["refusal"] is None, "bounded stream refused")
        for output in command["outputs"].values():
            path = root/output["path"]
            require(path.stat().st_size == output["bytes"] and candidate.sha(path) == output["sha256"], "raw command output changed")
    labels = [command["label"] for command in receipt["commands"]]
    require(labels.count("create") == labels.count("start") == 1, "native attempt count changed")
    require(labels.index("export-base-status") < labels.index("authenticate")
            and labels.index("export-base-keyring.gpg") < labels.index("authenticate"), "base export ordering changed")
    for suite in ("noble", "noble-updates", "noble-security"):
        for suffix in (".Release", ".gpg.status", ".gpg.stderr"):
            require(labels.index("export-"+suite+suffix) < labels.index("resolve"), "authentication export ordering changed")
    for filename in ("solver.stdout", "solver.stderr"):
        require(labels.index("resolve") < labels.index("export-"+filename) < labels.index("cleanup-remove"), "all-outcome solver export ordering changed")
    allowed = candidate.checked_budgets(json.loads(candidate.ADDENDUM.read_text()))
    require(set(receipt["metadataArtifacts"]) == set(allowed), "fixed exports incomplete")
    exported_bytes = 0
    for name, record in receipt["metadataArtifacts"].items():
        require(record["available"], "metadata export unavailable")
        path = root/record["path"]
        data = path.read_bytes()
        candidate.checked_export(name, data, allowed)
        require(candidate.sha(path) == record["sha256"] and len(data) == record["bytes"], "export record changed")
        exported_bytes += len(data)
    require(exported_bytes == receipt["fixedExportStreamRetainedBytes"] <= 2097152, "export total mismatch")
    require(all(value <= 524288 for value in receipt["ordinaryStreamRetainedBytes"].values()), "ordinary stream bound")
    artifacts = here/"attempt/artifacts"
    for suite in ("noble", "noble-updates", "noble-security"):
        status = (artifacts/(suite+".gpg.status")).read_text()
        signers = [line.split()[2] for line in status.splitlines() if line.startswith("[GNUPG:] VALIDSIG ")]
        require(signers == ["F6ECB3762474EDA9D21B7022871920D1991BC93C"], "native full signer mismatch")
    require("[GNUPG:] BADSIG " in (artifacts/"negative-signature.status").read_text(), "negative signature evidence missing")
    resolve = receipt["phases"]["resolve"]
    require(resolve["exitCode"] == 78 and "MIXER_SOLVER_EXIT=100" in resolve["markers"], "solver failure history changed")
    require("MIXER_TAMPERED_INDEX_REJECTED=1" in resolve["markers"], "negative index evidence missing")
    solver = (artifacts/"solver.stdout").read_text()
    require(not any(line.startswith(("Inst ", "Conf ")) for line in solver.splitlines()), "unobserved package lock")
    packages = [stanza(text) for text in (artifacts/"base-status").read_text().split("\n\n") if text.strip()]
    installed = {(x["Package"], x["Architecture"]): x["Version"] for x in packages if x.get("Status") == "install ok installed"}
    c1_inventory = {}
    prior = root/"verification/stripe-resource-linux-compiler-metadata/C1/06-probe.stdout"
    for line in prior.read_text().splitlines():
        if line.count("\t") == 2:
            package, version, architecture = line.split("\t")
            c1_inventory[(package.removesuffix(":"+architecture), architecture)] = version
    require(installed == c1_inventory, "base inventory differs from C1")
    require(receipt["cleanup"] == {"ownedContainerAbsent": True, "temporaryInputSnapshotRemoved": True}, "cleanup incomplete")
    print(json.dumps({"status": "retained-evidence-bindings-pass", "nativeAttempts": 1,
                      "exports": len(allowed), "exportedBytes": exported_bytes,
                      "baseInstalledPackages": len(installed), "baseInventoryMatchesC1": True,
                      "nativeSolverExitCode": 100, "exactDependencyLock": None,
                      "baseUpgradeDelta": "unresolved-no-native-Inst-records",
                      "negativeSignatureAndIndexControlsObserved": True,
                      "cleanupObserved": True}, sort_keys=True))


if __name__ == "__main__":
    main()
