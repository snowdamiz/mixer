"""Synthetic oracle controls, never a receipt for native interaction."""
import copy
import json
import pathlib
import unittest
import interruption_oracle as o


def fixture(name):
    # Use captured UIKit field shapes; deliberately alter values to form host
    # controls. Only runtime/captures may supply acceptance observations.
    p = o.BASE.parent / "apple-toggle-semantic-activation/runtime/captures"
    before = json.loads((p / "0003-before-1.json").read_bytes())["observation"]
    after = json.loads((p / "0003-after-1.json").read_bytes())["observation"]
    x = o.SPECS[name]; initial = x["initial"]; mode = x["mode"]
    b = before["state"]
    b.update(isOn=initial, retainedOn=initial, selectedTrait=initial, rtl=x["rtl"])
    before["nativeInterruptions"] = []
    a = copy.deepcopy(b)
    changed = mode == "accessibility"
    value = not initial if mode in {"accessibility", "binding"} else initial
    a.update(isOn=value, retainedOn=value, selectedTrait=value,
             enabled=mode != "disable", allowed=mode != "stale", notEnabledTrait=mode == "disable",
             eventCount=b["eventCount"] + int(changed), eventValues=b["eventValues"] + ([value] if changed else []),
             primaryCount=b["primaryCount"] + int(changed), acceptedCount=b["acceptedCount"] + int(changed),
             panNoChangeCount=b["panNoChangeCount"] + int(mode == "nochange"),
             panCancellationCount=b["panCancellationCount"] + int(mode != "nochange"))
    preview = copy.deepcopy(b); preview.update(panActive=True, previewThumbX=12)
    after["state"] = a
    after["events"] = before["events"] + [{"reason": "panPreview", "state": preview}]
    after["nativeInterruptions"] = []
    callbacks = [r for r in after["diagnosticTrace"] if r["kind"] == "authoredPanCallback"]
    if mode != "nochange":
        callbacks[-1]["state"] = 4
        after["nativeInterruptions"] = [dict(mode="arm-pan-" + mode, nativeHeld=True,
            before=preview, nativeGestureBefore=copy.deepcopy(callbacks[0]), after=copy.deepcopy(a),
            returned=True if changed else None, startedUptime=callbacks[0]["uptime"] + .001,
            finishedUptime=callbacks[0]["uptime"] + .002)]
    return before, after


class Controls(unittest.TestCase):
    def test_all_synthetic_case_controls(self):
        for name in o.SPECS:
            with self.subTest(case=name):
                b, a = fixture(name)
                self.assertTrue(o.verdict("diagnostic", name, "native-pan-interruption", b, a)["passed"])

    def test_rejects_corrupted_or_missing_native_evidence(self):
        mutations = [
            lambda a: a["state"].update(identity="replacement"),
            lambda a: a["state"].update(primaryCount=99),
            lambda a: a["state"].update(eventCount=99),
            lambda a: a["state"].update(eventValues=[True, True]),
            lambda a: a["state"].update(panAcceptedCount=99),
            lambda a: a["state"].update(panNoChangeCount=99),
            lambda a: a["state"].update(panActive=True),
            lambda a: a["state"].update(previewThumbX=12),
            lambda a: a["state"].update(nativeToggleSelection=True),
            lambda a: a["state"].update(scrollOffsetY=30),
            lambda a: a["state"].update(label="wrong"),
            lambda a: a.update(nativeInterruptions=[]),
            lambda a: a["nativeInterruptions"].append(copy.deepcopy(a["nativeInterruptions"][0])),
            lambda a: a["nativeInterruptions"][0].update(nativeHeld=False),
            lambda a: a["nativeInterruptions"][0].update(returned=False),
            lambda a: a["nativeInterruptions"][0].update(mode="arm-pan-stale"),
            lambda a: a["nativeInterruptions"][0].update(startedUptime=0),
            lambda a: a["nativeInterruptions"][0]["nativeGestureBefore"].update(touchCount=0),
            lambda a: a["nativeInterruptions"][0]["nativeGestureBefore"].update(state=3),
            lambda a: a["nativeInterruptions"][0]["nativeGestureBefore"].update(identity="fake"),
            lambda a: a["nativeInterruptions"][0]["after"].update(eventCount=999),
            lambda a: a["nativeInterruptions"][0]["after"].update(panActive=True),
            lambda a: a.update(diagnosticTraceDropped=1),
            lambda a: a["diagnosticTrace"][0].update(sequence=99),
            lambda a: a.update(diagnosticTrace=[r for r in a["diagnosticTrace"] if r["kind"] != "authoredPanCallback"]),
            lambda a: a.update(diagnosticTrace=[r for r in a["diagnosticTrace"] if r["kind"] != "recognizerShouldReceiveTouch"]),
            lambda a: a.update(events=a["events"][:-1]),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(mutation=i):
                b, a = fixture("accessibility-ltr-on"); mutate(a)
                self.assertFalse(o.verdict("diagnostic", "accessibility-ltr-on", "native-pan-interruption", b, a)["passed"])


if __name__ == "__main__": unittest.main()
