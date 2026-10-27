import json
import unittest
from custody import OWN, RUN33, read
from classfile_data import parse, invocation_at


class PreaccessDataTests(unittest.TestCase):
    def test_manifest_members_only(self):
        for path in ["../seal.json", "/etc/passwd", "reference-tree/../README.md", "not-released.txt"]:
            with self.assertRaises(AssertionError):
                read(path)

    def test_interface_exact38(self):
        q = parse(read(RUN33 + "classes/android/view/inputmethod/InputConnection.class"))
        self.assertEqual(q["name"], "android/view/inputmethod/InputConnection")
        self.assertEqual(len(q["methods"]), 38)
        self.assertIn(("setComposingRegion", "(II)Z"), {(m["name"], m["descriptor"]) for m in q["methods"]})
        self.assertIn(("setComposingRegion", "(IILandroid/view/inputmethod/TextAttribute;)Z"), {(m["name"], m["descriptor"]) for m in q["methods"]})

    def test_compiled_commit_and_neighbor(self):
        q = parse(read(RUN33 + "classes/dev/mixer/android/NativeEditorConnectionV2$Base.class"))
        exact = invocation_at(q, "lambda$commitText$6", "(Ljava/lang/CharSequence;I)Ljava/lang/Boolean;", 6)
        self.assertEqual((exact["opcode"], exact["owner"], exact["name"], exact["descriptor"]),
                         (185, "android/view/inputmethod/InputConnection", "commitText", "(Ljava/lang/CharSequence;I)Z"))
        neighbor = invocation_at(q, "lambda$commitText$6", "(Ljava/lang/CharSequence;I)Ljava/lang/Boolean;", 11)
        self.assertEqual((neighbor["opcode"], neighbor["owner"], neighbor["name"]), (184, "java/lang/Boolean", "valueOf"))
        for bci in [True, -1, "6", 7]:
            with self.assertRaises(AssertionError):
                invocation_at(q, "lambda$commitText$6", "(Ljava/lang/CharSequence;I)Ljava/lang/Boolean;", bci)

    def test_parser_truncation_is_failure(self):
        with self.assertRaises(AssertionError):
            parse(read(RUN33 + "classes/android/view/inputmethod/InputConnection.class")[:-1])

    def test_expected_samples_preserve_public_native_distinction(self):
        data = json.loads((OWN / "frozen-specimens.json").read_text())
        row = data["query-getExtractedText/successor"]["row"]
        self.assertEqual(row["actual_operation_outcome"], {"kind": "null"})
        self.assertEqual(row["selected_actual_native_completions"][0]["value"]["kind"], "typed-snapshot")
        close = data["direct-close/clean"]["row"]
        self.assertEqual(close["actual_enclosing_outcome"], {"kind": "void"})
        self.assertEqual(close["selected_actual_native_completions"], [])
        exception = data["direct-close/ordinary-throw-after-callback"]["row"]["selected_actual_native_completions"][0]
        self.assertEqual((exception["descriptor"], exception["completion"]), ("hook-exception", "exception"))

    def test_plan_is_unique_and_candidate_unread(self):
        data = json.loads((OWN / "preaccess-controls.json").read_text())
        self.assertEqual(len(data["controls"]), data["control_count"])
        self.assertEqual(len({x["id"] for x in data["controls"]}), len(data["controls"]))
        self.assertTrue(all(x["source_obligation"] and x["expected"] for x in data["controls"]))
        self.assertTrue(data["status"].startswith("preaccess-"))

    def test_switch_resolution_does_not_promote_inner_observation(self):
        data = json.loads((OWN / "switch-outer-versus-inner-source-case.json").read_text())
        self.assertEqual([c["row"] for c in data["cases"]], [3, 5])
        for case in data["cases"]:
            self.assertEqual(case["compiled_invocation"]["owner"], "android/widget/Switch")
            self.assertEqual(case["retained_resolution_path"][-1]["class"], "android/widget/TextView")
            self.assertEqual(case["selected_actual_native_completions"][0]["method"], "View.performAccessibilityAction")


if __name__ == "__main__":
    unittest.main()
