"""Replay the exact APK offers with the two source-built macOS presentation probes."""

import base64
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from threading import Thread
from urllib.parse import parse_qsl, urlencode, urlsplit
from urllib.request import build_opener, ProxyHandler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "fieldlog-task-calculation/android-packaging"))
from package import digest, read, require, write
from current_abi_packet import offer_pins, refusal_responses

SPEC = importlib.util.spec_from_file_location("android_origin", HERE / "android-origin.py")
origin = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(origin)


@contextmanager
def running(packet, phase_file, observe=None):
    with origin.server(packet, phase_file, observe=observe) as listener:
        worker = Thread(target=listener.serve_forever, kwargs={"poll_interval": .05})
        worker.start()
        try:
            yield f"http://127.0.0.1:{listener.server_port}"
        finally:
            listener.shutdown()
            worker.join(timeout=3)
            require(not worker.is_alive(), "Loopback origin did not close")


def phase(path, value):
    pending = path.with_suffix(".new")
    pending.write_text(value + "\n")
    pending.replace(path)


def refusal_exchange(packet, phase_file, host, installation, probe):
    """Run only the probe against the refusal listener and bind both responses."""
    phase(phase_file, "refuse")
    requests = []
    with running(packet, phase_file, observe=requests.append) as url:
        result = probe(url)

    expected = refusal_responses(packet, host, installation)
    require(len(requests) == len(expected), "Refusal probe did not complete exactly one update and one artifact response")
    responses = []
    for (target, status, body_hash), reference in zip(requests, expected, strict=True):
        parsed = urlsplit(target)
        items = parse_qsl(parsed.query, keep_blank_values=True)
        response = {"path": parsed.path, "query": dict(items), "status": status, "bodySHA256": body_hash}
        require(len(items) == len(response["query"]) and response == reference,
                f"Refusal probe request or response differs for {reference['path']}")
        responses.append(response)
    return result, offer_pins(packet, "refused") | {
        "runtime": host["runtime"], "installation": installation,
        "responses": responses,
    }


def replay(campaign):
    work, packet = campaign / "work", campaign / "handoff"
    state = work / "pair-replay"
    workspace = state / "workspace"
    workspace.mkdir(parents=True)
    old_material = packet / "old/Installed"
    shutil.copyfile(old_material / "calculation-seed.json", workspace / "workspace.json")
    workspace_sha = digest(workspace / "workspace.json")
    payloads = {label: packet / "reviewed.wasm" for label in ("old", "successor", "refused")}
    if (packet / "baseline.wasm").is_file():
        payloads["old"] = packet / "baseline.wasm"
    verifier = read(packet / "verifier.json")
    installation = verifier["installation"]
    hosts = {label: read(packet / label / "host.json") for label in ("old", "successor")}
    phase_file = state / "phase"
    opener = build_opener(ProxyHandler({}))

    def offer(url, host, expected, label=None):
        query = host["scope"] | {"channel": "beta", "runtime": host["runtime"], "installation": installation}
        with opener.open(url + "/v3/updates?" + urlencode(query), timeout=4) as response:
            require(response.status == expected, f"Unexpected update response: {response.status}")
            raw = response.read()
        if label:
            body = json.loads(raw)
            require(body["signed_assignment"] == read(packet / label / "assignment.json"),
                    f"Served assignment differs for {label}")
            with opener.open(url + body["artifact_url"], timeout=4) as response:
                artifact = json.load(response)
                require(read(packet / label / "manifest.json") == artifact["signed_manifest"]
                        and base64.b64decode(artifact["payload"], validate=True) == payloads[label].read_bytes(),
                        f"Served manifest or payload differs for {label}")
        return raw

    def probe(label, sequence, expect_fallback=False):
        if label == "old":
            executable = work / "storage-only-probe"
        else:
            successor = work / "successor/host-build/debug/Probe"
            executable = successor if (packet / "baseline.wasm").is_file() else work / "host-build/debug/Probe"
        variant = payloads[label].stem
        cmd = [executable, packet / label / "Installed", state, installation, str(sequence),
               "offline" if expect_fallback else "online", variant]
        result = json.loads(subprocess.check_output(cmd, text=True, timeout=22))
        percentages = ["0%", "100%", "0%"] if variant == "baseline" else ["33%", "100%", "0%"]
        expected_label = "Using saved checklist release" if expect_fallback else "Signed checklist"
        require(result["workspaceSHA256"] == workspace_sha and result["retired"]
                and result["percentages"] == percentages and result["label"] == expected_label,
                "Host presentation, delivery outcome or workspace differs")
        name = "recovery" if label == "old" else "recovery-" + hosts[label]["runtime"]
        path = state / "signed-checklist" / name / "state.json"
        recovery = read(path)
        candidate = recovery["candidates"][recovery["healthy"]["candidateID"]]
        signed = read(packet / label / "assignment.json")["assignment"]
        require(recovery["installation"] == installation and recovery["acceptedSequence"] == sequence
                and recovery["fingerprint"] == hosts[label]["runtime"] and recovery["attempt"] is None
                and candidate["artifactSHA256"] == signed["artifact_sha256"]
                and candidate["payloadSHA256"] == digest(payloads[label]),
                "Healthy recovery does not match the signed offer")
        return result, path

    phase(phase_file, "old")
    with running(packet, phase_file) as url:
        before = offer(url, hosts["old"], 200, "old")
        offer(url, hosts["successor"], 204)
        old, old_state = probe("old", 2)
    (refused, _), exchange = refusal_exchange(
        packet, phase_file, hosts["old"], installation,
        lambda _: probe("old", 2, expect_fallback=True),
    )
    require(refused["candidate"] == old["candidate"], "Incompatible offer replaced the old healthy candidate")
    phase(phase_file, "both")
    with running(packet, phase_file) as url:
        require(offer(url, hosts["old"], 200, "old") == before, "Old cohort response changed")
        offer(url, hosts["successor"], 200, "successor")
        offer(url, hosts["old"] | {"runtime": "0" * 64}, 204)

    port = int((old_material / "port.txt").read_text())
    with socket.socket() as connection:
        connection.settimeout(2)
        require(connection.connect_ex(("127.0.0.1", port)) != 0, "Loopback origin still accepts clients")
    offline, _ = probe("old", 2, expect_fallback=True)
    require(offline["candidate"] == old["candidate"] and offline["launchID"] != refused["launchID"],
            "Cold offline launch lost the old candidate")
    retained_bytes = old_state.read_bytes()
    with running(packet, phase_file):
        successor, _ = probe("successor", 3)
    require(old_state.read_bytes() == retained_bytes and digest(workspace / "workspace.json") == workspace_sha,
            "Successor altered the old recovery store or workspace")
    write(packet / "host-replay.json", {
        "scope": "macOS presentation witnesses, exact Android APK identity and installed materials",
        "oldOfferByteIdentical": True, "successorStatuses": [204, 200], "unknownRuntimeStatus": 204,
        "refusedOfferRetainedOldCandidate": True, "oldRecoveryByteIdenticalAfterSuccessor": True,
        "serviceClosedBeforeOffline": True,
        "refusalExchange": exchange,
        "separateVerifierRefusal": {"code": verifier["manifestRefusal"], "artifactSHA256": exchange["artifactSHA256"]},
        "observations": {"old": old, "oldAfterRefusal": refused, "oldOffline": offline, "successor": successor},
    })


if __name__ == "__main__":
    replay(Path(sys.argv[1]).resolve(strict=True))
