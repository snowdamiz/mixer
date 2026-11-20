#!/usr/bin/env python3
"""Compare recovery readbacks from one Android calculation launch and retirement."""

import argparse
import hashlib
import json
from pathlib import Path


def read_state(path):
    raw = path.read_bytes()
    state = json.loads(raw)
    if (state["kind"], state["schemaVersion"]) != ("mixer-capability-cold-start-v1", 3):
        raise ValueError("Unexpected recovery schema")
    return state, hashlib.sha256(raw).hexdigest()


def check_live(state, expected):
    if (
        state["fingerprint"] != expected.runtime
        or state["host"]["runtime"] != expected.runtime
        or state["installation"] != expected.installation
        or state["channel"] != "beta"
        or state["acceptedSequence"] != expected.sequence
    ):
        raise ValueError("Recovery scope or sequence differs from the installed assignment")
    if state["pending"] is not None:
        raise ValueError("Download is still pending")
    health, attempt = state["healthy"], state["attempt"]
    if health is None or attempt is None:
        raise ValueError("Expected committed health and a live attempt")
    if not {"feature_started", "first_screen"} <= set(health["completedMilestones"]):
        raise ValueError("Required health milestones have not committed")
    candidate_id = health["candidateID"]
    launch_id = health["launchID"]
    if (
        not launch_id
        or attempt["candidateID"] != candidate_id
        or attempt["launchID"] != launch_id
        or attempt["effectsMayHaveOpened"] is not True
    ):
        raise ValueError("Healthy launch differs from the active attempt")
    candidate = state["candidates"][candidate_id]
    if (
        candidate["candidateID"] != candidate_id
        or candidate["sequence"] != expected.sequence
        or candidate["artifactSHA256"] != expected.artifact
        or candidate["payloadSHA256"] != expected.payload
    ):
        raise ValueError("Healthy candidate differs from the expected signed artifact")
    return candidate_id, launch_id


def check_retired(live, retired, candidate_id):
    if (
        retired["attempt"] is not None
        or retired["pending"] is not None
        or retired["staged"] is not None
        or retired["lastRecovery"] != "effects_closed"
    ):
        raise ValueError("Installed guest did not retire normally")
    for field in ("acceptedSequence", "channel", "fingerprint", "healthy", "host", "installation", "previousHealthy"):
        if live[field] != retired[field]:
            raise ValueError(f"Retirement changed {field}")
    if live["candidates"][candidate_id] != retired["candidates"][candidate_id]:
        raise ValueError("Retirement changed the healthy candidate")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("live", type=Path)
    parser.add_argument("--retired", type=Path)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--installation", required=True)
    parser.add_argument("--sequence", type=int, required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--payload", required=True)
    args = parser.parse_args()
    try:
        live, live_hash = read_state(args.live)
        candidate, launch = check_live(live, args)
        result = {"candidate": candidate, "launch": launch, "liveSHA256": live_hash, "sequence": args.sequence}
        if args.retired is not None:
            retired, retired_hash = read_state(args.retired)
            check_retired(live, retired, candidate)
            result["retiredSHA256"] = retired_hash
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(1, f"Recovery readback refused: {error}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
