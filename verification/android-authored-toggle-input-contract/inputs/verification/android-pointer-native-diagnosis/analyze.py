#!/usr/bin/env python3
"""Offline evidence binding and conditional platform arithmetic, never native execution."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUNTIME = ROOT / "verification/android-pointer-timing-correction/runtime/runtime-1"
CANDIDATE = ROOT / "verification/android-pointer-oracle-repair/candidate-5"
APK = "57e82e4e98cdc61581c0639603ec6efa500a66d8d2754f6b47ece89c8165d714"
CLOSURE = "9082e2de1327bd0784d752db5dfbe4484751d565b3410e01e78664321467f5ce"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text())


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].startswith("analysis-"):
        raise ValueError("one fresh analysis-* output name is required")
    out = HERE / sys.argv[1]
    out.mkdir(exist_ok=False)
    receipt = {
        "schema": 1,
        "observedUTC": datetime.now(timezone.utc).isoformat(),
        "argv": [sys.executable, str(Path(__file__).resolve()), sys.argv[1]],
        "cwd": str(ROOT),
        "python": sys.version,
        "platform": platform.platform(),
        "scope": "offline sealed failure analysis and conditional AOSP arithmetic only",
        "nativeCommandsExecuted": 0,
        "physicalTargetsQueried": False,
        "status": "running",
        "scriptSHA256": sha(Path(__file__)),
    }
    try:
        bindings = {}

        def bind(path: Path) -> None:
            bindings[str(path.relative_to(ROOT))] = {"bytes": path.stat().st_size, "sha256": sha(path)}

        seal = load(RUNTIME / "artifact-seal.json")
        for name, expected in seal.items():
            path = RUNTIME / name
            actual = {"bytes": path.stat().st_size, "sha256": sha(path)}
            assert actual == expected, f"runtime seal mismatch: {name}"
            bind(path)
        bind(RUNTIME / "artifact-seal.json")
        lock = load(CANDIDATE / "source-lock.json")
        assert len(lock["files"]) == 105
        assert hashlib.sha256(json.dumps(lock["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest() == CLOSURE
        for name, expected in lock["files"].items():
            path = CANDIDATE / "inputs" / name
            assert sha(path) == expected, f"frozen source mismatch: {name}"
            bind(path)
        bind(CANDIDATE / "source-lock.json")
        for name in ["CoordinatorJoinActivity.java", "CoordinatorJoinInstrumentation.java"]:
            fixture = ROOT / "verification/android-pointer-oracle-repair" / name
            assert sha(fixture) == lock["files"]["verification/android-coordinator-join/" + name]
            bind(fixture)
        apk = ROOT / ("verification/android-pointer-oracle-repair/retained-apk/candidate-5-" + APK + "/coordinator-join.apk")
        assert sha(apk) == APK
        bind(apk)
        bind(ROOT / "docs/android-native-input-matrix-contract.md")
        native = load(RUNTIME / "native-results-export.log")
        assert native == load(RUNTIME / "native-results.json")
        assert native["apkSHA256"] == APK and native["sourceClosureSHA256"] == CLOSURE
        assert native["status"] == "failed" and native["failure"] == "java.lang.AssertionError: exact authoritative revision acknowledgement count"
        assert [(x["actionId"], x["status"]) for x in native["summaries"]] == [("P01", "passed"), ("P02", "passed")]
        rows = [json.loads(line) for line in (RUNTIME / "pointer-observations.jsonl").read_text().splitlines()]
        p03 = [(i + 1, row) for i, row in enumerate(rows) if row.get("actionId") == "P03-1"]
        seq = load(RUNTIME / "pointer-sequence-3.json")
        entries = [(i, r) for i, r in p03 if r["kind"] == "activity-entry"]
        exits = [(i, r) for i, r in p03 if r["kind"] == "activity-exit"]
        sends = [(i, r) for i, r in p03 if r["kind"] == "worker-send"]
        afters = [(i, r) for i, r in p03 if r["kind"] == "after-send"]
        assert len(entries) == len(exits) == len(sends) == len(afters) == len(seq["events"]) == 10
        table = []
        for n, ((line, entry), (_, exit_row), (_, send), (_, after), planned) in enumerate(zip(entries, exits, sends, afters, seq["events"])):
            event = entry["event"]
            pointer = event["pointers"][0]
            assert event == exit_row["event"]
            assert event["action"] == planned["action"]
            assert event["downTime"] == seq["downTime"]
            assert event["eventTime"] == seq["downTime"] + planned["offsetMilliseconds"]
            assert event["source"] == 4098 and event["pointerCount"] == 1
            assert pointer["id"] == 0 and pointer["toolType"] == 1
            assert pointer["pressure"] == planned["pressure"]
            assert abs(pointer["rawX"] - planned["x"]) <= 1 and abs(pointer["rawY"] - planned["y"]) <= 1
            assert not event["history"]
            assert exit_row["returned"] is True and exit_row["exception"] is None and send["exception"] is None
            for state in [entry["state"], exit_row["state"], after["state"]]:
                for key in ["packetReference", "packetSHA256", "revision", "values", "nativeValues", "targetGeneration", "targetRecord", "targetView", "editors"]:
                    assert state[key] == seq["before"][key], key
                assert state["targetSameRecord"] and state["targetSameView"]
                assert state["nativeChecked"] is False and state["scrollY"] == 0 and state["current"] is True
                assert state["retired"] is False and state["rendererRetired"] is False and state["lastNativeInputFailure"] is None
            table.append({"eventIndex": n, "observationEntryLine": line, "action": event["action"], "offsetMilliseconds": planned["offsetMilliseconds"], "screenX": pointer["rawX"], "screenY": pointer["rawY"], "eventTime": event["eventTime"], "activityEntryUptime": entry["workerIndependentUptime"], "activityExitUptime": exit_row["uptime"], "workerLatenessMilliseconds": send["workerBefore"] - send["scheduledUptime"], "pressure": pointer["pressure"], "historyCount": 0, "revisionBeforeAndAfter": "3", "nativeCheckedBeforeAndAfter": False})
        interval = next(r for _, r in p03 if r["kind"] == "action-interval")
        assert interval["completed"] is False and interval["durationMilliseconds"] == 1015
        save(out / "p03-events.json", table)

        # This is deliberately a conditional reference calculation. It does not
        # assert that unobserved platform-private state had these values.
        geometry = seq["geometry"]
        thumb_width = geometry["offThumb"]["right"] - geometry["offThumb"]["left"]
        thumb_height = geometry["offThumb"]["bottom"] - geometry["offThumb"]["top"]
        track_width = geometry["track"]["right"] - geometry["track"]["left"]
        track_height = geometry["track"]["bottom"] - geometry["track"]["top"]
        carrier_width = max(track_width, 2 * thumb_width)
        carrier_range = carrier_width - thumb_width
        slop = seq["thresholds"]["touchSlop"]
        start_x = seq["events"][0]["x"]
        crossing = next(e for e in seq["events"][1:-1] if abs(e["x"] - start_x) > slop)
        retained_distance = seq["events"][-2]["x"] - crossing["x"]
        left = geometry["viewBounds"]["right"] - carrier_width
        top = geometry["viewBounds"]["top"]
        hit = {"left": left - slop, "top": top - slop, "right": left + thumb_width, "bottom": top + max(track_height, thumb_height) + slop}
        model = {
            "classification": "conditional AOSP prediction, not observed platform-private state",
            "assumptions": ["pinned android17-release Switch algorithm matches installed API37 implementation", "base Drawable zero padding and optical insets", "TOP gravity and LTR as frozen product defaults", "mThumbPosition is zero when dragging starts", "release follows positional rather than fling branch", "child Switch receives the recorded Activity path without parent cancellation"],
            "authoredTrackWidth": track_width, "thumbIntrinsicWidth": thumb_width,
            "predictedCarrierWidth": carrier_width, "predictedCarrierRange": carrier_range,
            "predictedCarrierScreenLeft": left, "predictedCarrierScreenTop": top,
            "predictedOffHitBoundsStrict": hit,
            "authoredDownInsidePredictedOffHitBounds": hit["left"] < start_x < hit["right"] and hit["top"] < seq["events"][0]["y"] < hit["bottom"],
            "authoredCenterTravel": seq["events"][-1]["x"] - start_x,
            "slopCrossingOffsetMilliseconds": crossing["offsetMilliseconds"],
            "distanceDiscardedWhenEnteringDragging": crossing["x"] - start_x,
            "distanceAccumulatedAfterEnteringDragging": retained_distance,
            "predictedThumbPositionBeforeUP": retained_distance / carrier_range,
            "predictedPositionalChecked": retained_distance / carrier_range > 0.5,
            "counterfactualAuthoredRangePosition": retained_distance / (seq["events"][-1]["x"] - start_x),
            "counterfactualNoSlopDiscardPosition": (seq["events"][-1]["x"] - start_x) / carrier_range,
            "actualCarrierPrivateStateObserved": False,
            "actualChildTargetDeliveryObserved": False,
            "actualVelocityObserved": False,
        }
        assert model["authoredDownInsidePredictedOffHitBounds"] is True
        assert model["predictedCarrierWidth"] == 222 and model["predictedCarrierRange"] == 111
        assert model["distanceDiscardedWhenEnteringDragging"] == 24.75 and model["distanceAccumulatedAfterEnteringDragging"] == 41.25
        assert model["predictedPositionalChecked"] is False
        assert model["counterfactualAuthoredRangePosition"] > 0.5 and model["counterfactualNoSlopDiscardPosition"] > 0.5
        save(out / "conditional-carrier-model.json", model)
        for name in ["Switch-android17-release.java.txt", "Drawable-android17-release.java.txt", "aosp-android17-release-revision.json", "aosp-pinned-reference.json", "aosp-drawable-reference.json"]:
            bind(HERE / name)
        save(out / "input-bindings.json", bindings)
        receipt.update({"status": "passed-offline-analysis", "runtimeArtifactBindingsVerified": len(seal), "candidateInputBindingsVerified": 105, "sourceRevision": native["sourceRevision"], "sourceTree": native["sourceTree"], "sourceClosureSHA256": CLOSURE, "apkSHA256": APK, "runtimeSealSHA256": sha(RUNTIME / "artifact-seal.json"), "inputBindingsSHA256": sha(out / "input-bindings.json"), "inputTreeDigestSHA256": hashlib.sha256(json.dumps(bindings, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "observedActionsPassed": ["P01-1", "P02-1"], "observedActionFailed": "P03-1", "full20ActionMatrixAccepted": False, "platformPrivateCauseEstablished": False, "limitations": ["read-only offline analysis", "Activity delivery does not prove Switch child routing", "carrier, drag mode, thumb position, animation and release velocity not captured", "AOSP source is not proven byte-identical to installed framework", "P03 final settled snapshot is not exported because assertion occurs before success summary", "phones remain disconnected and deferred"]})
        print(json.dumps({"status": receipt["status"], "runtimeBindings": len(seal), "sourceInputs": 105, "P03Events": len(table), "maxP03WorkerLatenessMilliseconds": max(x["workerLatenessMilliseconds"] for x in table), "conditionalCarrierPosition": model["predictedThumbPositionBeforeUP"], "causeEstablished": False}))
    except BaseException as exc:
        receipt.update({"status": "failed-offline-analysis", "failure": repr(exc)})
        raise
    finally:
        receipt["finishedUTC"] = datetime.now(timezone.utc).isoformat()
        save(out / "receipt.json", receipt)


if __name__ == "__main__":
    main()
