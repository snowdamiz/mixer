#!/usr/bin/env python3
"""Replay the completed V4 receipt as data; never launches or extracts a product."""
import copy
import hashlib
import json
from pathlib import Path
import tarfile

import prepare as p
import qualification as q
import run_qualification as run


def main():
    here, root = p.HERE, p.ROOT
    source_seal = json.loads((here/"seal.json").read_text())
    for name, expected in source_seal["files"].items():
        p.require(p.sha(root/name) == expected, "prepared binding changed: "+name)
    receipt = json.loads((here/"attempt-1/receipt.json").read_text())
    p.require(receipt["status"] == "C6-private-compiler-qualification-completed-root-review-pending", "qualification incomplete")
    p.require(receipt["sourceFiles"] == run.source_files(), "executed source differs")
    p.require(receipt["sourceDigest"] == p.digest(run.source_files()) == source_seal["sourceDigest"], "source digest differs")
    commands = receipt["commands"]
    bylabel = {c["label"]: c for c in commands}
    p.require(len(commands) == len(bylabel), "duplicate command label")
    exported = 0
    for command in commands:
        p.require(command["error"] is None and command["elapsedSeconds"] <= 30, "command failed or exceeded bound")
        expected_exit = 1 if command["label"] in ("name-before", "cleanup-absence") else 0
        p.require(command["exitCode"] == expected_exit, "unexpected command exit")
        for record in command["outputs"].values():
            path = root/record["path"]
            p.require(path.stat().st_size == record["bytes"] and p.sha(path) == record["sha256"], "raw output changed")
            if "/exports/" in record["path"]:
                exported += record["bytes"]
    p.require(exported == receipt["fixedArtifactExportBytes"] <= q.BOUNDS["fixedExportAggregateBytes"], "export bound or accounting")
    p.require(receipt["elapsedSecondsIncludingCleanup"] <= 120 and receipt["conservativeOwnedStorageCeilingBytes"] <= q.BOUNDS["ownedStorageBytes"], "wall/storage bound")
    p.require(all(value <= 524288 for value in receipt["ordinaryStreamBytes"].values()), "ordinary stream bound")
    info = json.loads((root/bylabel["policy-before"]["outputs"]["stdout"]["path"]).read_text())[0]
    create = bylabel["create"]["argv"]
    mount = create[create.index("--mount")+1]
    p.require(mount.startswith("type=bind,src=") and mount.endswith(",dst=/inputs,readonly"), "input mount argv")
    snapshot = Path(mount.removeprefix("type=bind,src=").removesuffix(",dst=/inputs,readonly"))
    name, token, identifier = receipt["containerName"], receipt["ownerToken"], receipt["cleanupRecoveredContainerID"]
    run.checked_image(json.loads((root/bylabel["image-inspect"]["outputs"]["stdout"]["path"]).read_text())[0])
    run.checked_policy(info, name, token, snapshot, identifier)
    p.require(not snapshot.exists(), "owned input snapshot still exists")
    report = json.loads((here/"data-audit-final.json").read_text())
    base = {}
    base_bytes = 0
    for record in receipt["baseExportObservations"]:
        body, member = q.base_file_tar((root/record["exportTar"]["path"]).read_bytes(), record["requestedSONAME"])
        p.require(member == record["observedMemberName"] and len(body) == record["bodyBytes"], "base member observation differs")
        h = hashlib.sha256(body).hexdigest()
        p.require(h == record["bodySHA256"] == receipt["baseClosure"]["files"][record["requestedPath"]], "base hash differs")
        metadata = p.elf(body)
        p.require(metadata["soname"] == record["requestedSONAME"], "base SONAME differs")
        p.require(metadata == receipt["baseClosure"]["ELF"][record["requestedSONAME"]], "base ELF differs")
        base[record["requestedSONAME"]] = metadata
        base_bytes += len(body)
    p.require(len(base) == 7 and base_bytes == receipt["baseClosure"]["bytes"] <= q.MAX_BASE_BYTES, "base closure size")
    q.verify_complete_base(report, base)
    headers = run.inspect_headers((root/bylabel["erts-headers"]["outputs"]["stdout"]["path"]).read_bytes(), report["matchingERTSHeaders"])
    p.require(headers == receipt["ERTSHeaders"] and len(headers) == 10, "ERTS header graph differs")
    for package, notice in receipt["inheritedBaseNotices"].items():
        p.require(notice["available"], "inherited notice unavailable")
        body = q.one_file_tar((root/bylabel["notice-"+package]["outputs"]["stdout"]["path"]).read_bytes(), "copyright", maximum=1048576)
        p.require(len(body) == notice["bytes"] and hashlib.sha256(body).hexdigest() == notice["sha256"], "notice differs")
    text = (root/bylabel["qualify"]["outputs"]["stdout"]["path"]).read_text()
    p.require(bylabel["qualify"]["exitCode"] == 0 and "MIXER_C6_COMPILES=4\n" in text, "native completion missing")
    p.require(text.count("ELF Header:") == 4, "native readelf output count")
    native_hashes = {}
    bodies, products = {}, {}
    for iteration in (1, 2):
        for filename in ("fault_helper", "control_nif.so"):
            command = bylabel["product-{}-{}".format(iteration, filename)]
            p.require(command["argv"] == run.product_export_argv(name, iteration, filename), "product transport argv differs")
            raw_record = command["outputs"]["stdout"]
            p.require(raw_record["bytes"] <= 2097152+1048576, "product tar bound")
            body = q.one_file_tar((root/raw_record["path"]).read_bytes(), filename, maximum=2097152)
            key = str(iteration)+"/"+filename
            item = {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "ELF": p.elf(body)}
            p.require(item == receipt["products"][key], "external product identity differs")
            native_path = "/tmp/mixer-compiler-qualification/run-"+str(iteration)+"/"+filename
            matching = [line for line in text.splitlines() if line == item["sha256"]+"  "+native_path]
            p.require(len(matching) == 1, "native/exported product hash differs")
            native_hashes[key] = item["sha256"]
            bodies[key], products[key] = body, {**item, "archive": raw_record}
    for filename in ("fault_helper", "control_nif.so"):
        p.require(bodies["1/"+filename] == bodies["2/"+filename], "repeated external bytes differ")
    composed = copy.deepcopy(report)
    for filename in ("fault_helper", "control_nif.so"):
        composed["compilerClosure"]["payloadClosure"]["product/"+filename] = products["1/"+filename]["ELF"]
    q.verify_complete_base(composed, base)
    identity = bylabel["cleanup-identity"]
    p.require(run.cleanup_resolution((root/identity["outputs"]["stdout"]["path"]).read_bytes(), identity["exitCode"],
                                    (root/identity["outputs"]["stderr"]["path"]).read_bytes(), name, token, identifier) == identifier, "cleanup identity differs")
    p.require(bylabel["cleanup-remove"]["argv"] == ["docker", "rm", "-f", name], "cleanup target differs")
    absence = bylabel["cleanup-absence"]
    p.require(run.cleanup_resolution((root/absence["outputs"]["stdout"]["path"]).read_bytes(), absence["exitCode"],
                                    (root/absence["outputs"]["stderr"]["path"]).read_bytes(), name, token, identifier) is None, "absence not proved")
    p.require(receipt["cleanup"] == {"ownedContainerAbsent": True, "temporaryInputSnapshotRemoved": True}, "cleanup receipt incomplete")
    p.require(not receipt["helperExecuted"] and not receipt["NIFLoaded"] and not receipt["BEAMExecuted"]
              and receipt["resourceRuntimeRowsExecuted"] == 0, "execution scope drift")
    print(json.dumps({"schema": 1, "status": "C6-private-compiler-and-retained-product-audit-pass-root-acceptance-pending",
          "auditSourceSHA256": p.sha(Path(__file__)), "sourceDigest": receipt["sourceDigest"], "preparedBindingsVerified": len(source_seal["files"]),
          "commandRecordsVerified": len(commands), "nativeCompiles": 4, "nativeReadelfProductOutputs": 4,
          "nativeAndExportedHashesEqual": True, "externalByteComparisonPairsPassed": 2, "products": products,
          "retainedProductBodyBytes": sum(len(body) for body in bodies.values()), "baseELFFiles": 7, "baseELFBytes": base_bytes,
          "baseAndProductGNUVersionProvidersVerified": True, "originalERTSHeaderFiles": 10,
          "fixedArtifactExportBytes": exported, "originalIsolationPolicyVerified": True, "inputSnapshotAbsent": True,
          "ownedContainerAbsenceVerifiedFromRetainedResponse": True, "nativeAttemptRepeated": False,
          "hostExtractionExecuted": False, "helperOrNIFOrBEAMExecuted": False, "resourceRuntimeRowsExecuted": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
