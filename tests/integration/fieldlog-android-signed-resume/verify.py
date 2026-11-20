#!/usr/bin/env python3
"""Check the signed Android transfer boundary using captured durable readbacks."""

import argparse
from collections import Counter
import json
from pathlib import Path
import runpy
from types import SimpleNamespace
from xml.etree import ElementTree

from origin import TRANSFER_PREFIX, admit_packet, digest


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read(path):
    return json.loads(path.read_bytes())


def verify(packet, directory, readback):
    validate = runpy.run_path(str(readback))
    _, target, replies = admit_packet(packet)
    delivery = packet / "delivery-android"
    seed = (delivery / "Installed/calculation-seed.json").read_bytes()
    stages = (
        ("baseline", 1, False, False),
        ("interrupted", 1, True, True),
        ("cold-offline", 1, True, True),
        ("changed-prefix", 1, True, False),
        ("partial-again", 1, True, True),
        ("resumed", 2, False, False),
    )
    reviewed = read(delivery / "sequence-2.assignment.json")["assignment"]["artifact_sha256"]
    partial = reviewed.encode() + replies[2][2][:TRANSFER_PREFIX]
    snapshots = {}
    baseline = read(directory / "baseline/live.json")
    installation = baseline["installation"]
    baseline_candidate = baseline["healthy"]["candidateID"]
    scope = {key: value for key, value in target.items() if key not in {"runtime", "channel"}}
    for stage, sequence, saved, has_spool in stages:
        capture = directory / stage
        live, state_digest = validate["read_state"](capture / "live.json")
        retired, retired_digest = validate["read_state"](capture / "retired.json")
        variant = "baseline" if sequence == 1 else "reviewed"
        expected = SimpleNamespace(runtime=target["runtime"], installation=installation, sequence=sequence,
                                   artifact=read(delivery / f"sequence-{sequence}.assignment.json")["assignment"]["artifact_sha256"],
                                   payload=digest((delivery / f"{variant}.wasm").read_bytes()))
        candidate, launch = validate["check_live"](live, expected)
        validate["check_retired"](live, retired, candidate)
        require(live["host"]["scope"] == scope and live["staged"] == (None if saved else candidate),
                f"Wrong staged candidate or scope at {stage}")
        if sequence == 1:
            require(candidate == baseline_candidate and set(live["candidates"]) == {candidate},
                    "Incomplete or changed prefix produced a new candidate")
        else:
            require(candidate != baseline_candidate and set(live["candidates"]) == {baseline_candidate, candidate}
                    and live["previousHealthy"]["candidateID"] == baseline_candidate,
                    "Complete transfer did not preserve the prior healthy candidate")
        spool = capture / "artifact.partial"
        require(spool.is_file() == has_spool, f"Unexpected spool presence at {stage}")
        require(not has_spool or spool.read_bytes() == partial, f"Wrong saved prefix bytes at {stage}")
        require((capture / "workspace.json").read_bytes() == seed, f"Workspace changed at {stage}")
        label = ("Using saved checklist release" if saved else "Signed checklist") + f" | Sequence {sequence}"
        texts = [node.get("text") for node in ElementTree.parse(capture / "screen.xml").iter("node")
                 if node.get("package") == "dev.fieldlog.generatedr90.calculation"]
        require(label in texts and [text for text in texts if text and text.endswith("%")] ==
                (["0%", "100%", "0%"] if sequence == 1 else ["33%", "100%", "0%"]),
                f"Missing calculation frame at {stage}")
        snapshots[stage] = {"sequence": sequence, "candidate": candidate, "launch": launch,
                            "pid": int((capture / "pid").read_bytes()), "spoolSHA256": digest(partial) if has_spool else None,
                            "stateSHA256": state_digest, "retiredSHA256": retired_digest}
    before = snapshots["interrupted"]
    cold = snapshots["cold-offline"]
    require(before["pid"] != cold["pid"] and before["launch"] != cold["launch"], "Cold reopen was not observed")
    routes = read(directory / "offline-network.json")
    require(set(routes) == {"-4", "-6"} and all(not value["mainDefault"].strip() and value["lookupExit"] != 0
            and "unreachable" in value["lookupOutput"].lower() for value in routes.values()),
            "Offline route witness did not pass")

    rows = [json.loads(line) for line in (directory / "responses.jsonl").read_text().splitlines()]
    observed = Counter((row["phase"], row["kind"]) for row in rows)
    require(observed == Counter({(phase, kind): 2 if phase == "partial" else 1
                                for phase in ("baseline", "partial", "changed-prefix", "complete")
                                for kind in ("offer", "artifact")}), "Unexpected request count or phases")
    for row in rows:
        sequence = 1 if row["phase"] == "baseline" else 2
        _, offer, artifact = replies[sequence]
        require(row["status"] == 200 and not row["rangeHeaderPresent"], "Unexpected delivery protocol")
        if row["kind"] == "offer":
            require(row["installation_sha"] == digest(installation.encode()) and row["wireSHA256"] == digest(offer),
                    "Offer bytes or installation do not match the signed assignment")
        else:
            require(row["declaredBytes"] == len(artifact), "Artifact envelope length changed")
            if row["phase"] == "changed-prefix":
                replacement = b"r" if artifact[32:33] != b"r" else b"u"
                altered = artifact[:32] + replacement + artifact[33:]
                require(row["wireSHA256"] == digest(altered) and row["offeredBytes"] == len(artifact),
                        "The changed-prefix response differs from the fixture")
            else:
                wire = artifact[:TRANSFER_PREFIX] if row["phase"] == "partial" else artifact
                require(row["writeCompleted"] and row["wireSHA256"] == digest(wire)
                        and row["offeredBytes"] == len(wire), "Wrong artifact bytes on the wire")
    return {"installationSHA256": digest(installation.encode()), "runtime": target["runtime"],
            "prefixBytes": TRANSFER_PREFIX, "workspaceSHA256": digest(seed), "routes": routes,
            "snapshots": snapshots, "wire": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--readback", type=Path, default=Path(__file__).resolve().parents[1] /
                        "fieldlog-task-calculation/android-readback.py")
    args = parser.parse_args()
    print(json.dumps(verify(args.packet, args.capture, args.readback), indent=2))


if __name__ == "__main__":
    main()
