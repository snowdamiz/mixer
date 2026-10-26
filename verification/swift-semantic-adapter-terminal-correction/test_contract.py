"""Finite contract-model and custody checks, never Rust/product tests."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import unittest

import classifier
import prepare

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]

def load(name):
    return json.loads((BASE/name).read_text())

class TerminalContractChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=load("input-manifest.json")
        cls.contract=load("terminal-contract.json")
        cls.cases=load("expected-cases.json")["cases"]
        cls.base=copy.deepcopy(next(c["request"] for c in cls.cases if c["id"]=="V-cap-open-taken"))

    def test_01_all_original_seals_preserved(self):
        current=prepare.check_old()
        self.assertEqual(current,self.inputs["old_seals_before"])
        self.assertEqual([r["members"] for r in current],[152,35,21])

    def test_02_exact_input_and_source_excerpt_custody(self):
        by={r["path"]:r for r in self.inputs["members"]}
        self.assertEqual(len(by),13)
        for r in by.values():
            raw=(BASE/r["snapshot"]).read_bytes()
            self.assertEqual(len(raw),r["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(),r["sha256"])
            self.assertEqual((ROOT/r["path"]).read_bytes(),raw)
        bindings=load("source-bindings.json")["rows"]
        self.assertEqual(len(bindings),7)
        for r in bindings:
            raw=(BASE/r["snapshot"]).read_bytes()
            part=b"".join(raw.splitlines(keepends=True)[r["first"]-1:r["last"]])
            self.assertEqual(hashlib.sha256(raw).hexdigest(),r["source_sha256"])
            self.assertEqual(hashlib.sha256(part).hexdigest(),r["excerpt_sha256"])
            self.assertEqual(part.decode(),r["excerpt"])

    def test_03_literal_full_word_expected_cases(self):
        self.assertEqual(len(self.cases),56)
        self.assertEqual(len({c["id"] for c in self.cases}),56)
        for case in self.cases:
            self.assertEqual(classifier.classify(case["request"]),case["expected"],case["id"])
            if case["expected"]["kind"]=="Ok":
                words=case["expected"]["words"]
                self.assertEqual(len(words),32)
                self.assertEqual(words[26:],[0]*6)
            else:
                self.assertIsNone(case["expected"]["words"])
                self.assertEqual(len(case["expected"]["error"]),5)

    def test_04_literal_accepted_child_normalization(self):
        cases=load("source-normalization-cases.json")["cases"]
        self.assertEqual(len(cases),41)
        for case in cases:
            self.assertEqual(classifier.normalize_child(case["facts"]),case["expected"],case["id"])

    def test_05_finite_total_cartesian_and_authority(self):
        count=0;rows=set()
        children=self.contract["children"]
        progress=self.contract["progress_tags"]
        latches=self.contract["latches"]
        for child,p,latch,error,stage,calls_zero in itertools.product(children,progress,latches,[False,True],range(11),[False,True]):
            r=copy.deepcopy(self.base)
            r.update({"child":child,"progress":p,"latch":latch})
            r["snapshot"]["stage"]=stage
            if latch!="None":
                r.update({"N":12,"NC":12,"calls":8,"stop":8,
                          "latch_reason":{"Refusal":11,"Failure":14,"Limit":1}[latch]})
            if calls_zero:r["calls"]=0
            if error:r["outer_error"]=[8,8,128,0,0]
            out=classifier.classify(r)
            self.assertIn(out["row"],{"T%02d"%i for i in range(16)})
            rows.add(out["row"]);count+=1
            if out["kind"]=="Err":self.assertIsNone(out["words"])
            else:
                self.assertEqual(len(out["words"]),32)
                self.assertEqual(out["words"][26:],[0]*6)
                self.assertEqual(out["words"][21],512*r["SS"]+256*r["SF"]+7680*r["NC"])
                self.assertTrue(all(type(x) is int and 0<=x<=classifier.MAX for x in out["words"]))
        self.assertEqual(count,10560)
        # T15's coherent idle/no-latch input is independently in literal cases.
        rows.update(c["expected"]["row"] for c in self.cases)
        self.assertEqual(rows,{"T%02d"%i for i in range(16)})

    def test_06_suppression_never_reads_snapshot_or_installs_MAX(self):
        r=copy.deepcopy(self.base);r["snapshot"]=object()
        examples=[("InputBinding","Valid","T01"),("InputBudget","Poison","T02"),
                  ("InputInvalid","Malformed","T03"),("EnvelopePoison","Absent","T04"),
                  ("Cap","Malformed","T05"),("Unsupported","Valid","T06"),
                  ("EnvelopeRefused","Valid","T07")]
        for child,p,row in examples:
            r.update({"child":child,"progress":p})
            out=classifier.classify(r)
            self.assertEqual(out["row"],row)
            self.assertEqual(out["words"][2:21],[0]*19)
            self.assertEqual(out["words"][24:],[0]*8)
        r.update({"child":"Limited","progress":"Absent","calls":0})
        self.assertEqual(classifier.classify(r)["row"],"T08")

    def test_07_outer_error_no_projection_or_paid_receipt_read(self):
        # Only the already propagated outer error is inspected on T00.
        r={"outer_error":[14,8,49152,0,0]}
        self.assertEqual(classifier.classify(r),{"kind":"Err","row":"T00","error":[14,8,49152,0,0],"words":None})

    def test_08_idle_does_not_read_inactive_payload(self):
        case=next(c for c in self.cases if c["id"]=="V-closed-idle-inactive-storage")
        r=copy.deepcopy(case["request"])
        for k in ["op","function","selected","taken","committed","pending","destination","feasible"]:
            r["snapshot"].pop(k,None)
        self.assertEqual(classifier.classify(r),case["expected"])

    def test_09_absorbing_terminal_dispatch_declaration(self):
        for child in ["Closed","Cap","Limited"]:
            for latch,row in [("Refusal","T10"),("Failure","T11"),("Limit","T12")]:
                r=copy.deepcopy(self.base)
                r.update({"child":child,"N":12,"NC":12,"calls":8,"latch":latch,"stop":8,
                          "latch_reason":{"Refusal":11,"Failure":14,"Limit":1}[latch]})
                self.assertEqual(classifier.classify(r)["row"],row)
                # A fabricated additional dispatch after that latch poisons
                # instead of replacing its terminal event or resuming success.
                r["after_latch_calls"]=1
                self.assertEqual(classifier.classify(r)["row"],"T05")

    def test_10_unchanged_caps_bounds_layout_and_words(self):
        by={r["path"]:r for r in self.inputs["members"]}
        old=json.loads((BASE/by["verification/swift-semantic-adapter-prerequisite/contract.json"]["snapshot"]).read_text())
        self.assertEqual(self.contract["observation_words"],old["observation"]["words"])
        self.assertEqual(self.contract["boundaries"],old["observation"]["boundaries"])
        self.assertEqual(self.contract["reasons"],old["observation"]["reason_ids"])
        self.assertEqual(self.contract["unchanged_global_caps"],old["global_caps"])
        self.assertEqual(self.contract["unchanged_work"],old["work"])
        self.assertEqual(self.contract["unchanged_memory"],old["memory"])
        self.assertEqual(len(self.contract["projection_V"]),32)
        self.assertLess(512+256+7680*4194304,2**64)

    def test_11_all_private_boundary_classes_and_nonemitting_ids(self):
        for case in self.cases:
            out=classifier.classify(case["request"])
            if out["kind"]=="Ok":self.assertNotIn(out["words"][1],[15,17])
        r=copy.deepcopy(self.base);r["progress"]="unsupported-private-tag"
        self.assertEqual(classifier.classify(r)["row"],"T05")
        r=copy.deepcopy(self.base);r["child"]="unsupported-child-combination"
        self.assertEqual(classifier.classify(r)["row"],"T06")

    def test_12_no_runtime_or_review_acceptance_claim(self):
        self.assertTrue(self.contract["independent_review_pending"])
        self.assertEqual(self.contract["native_or_Rust_product_tests"],0)
        doc=(ROOT/"docs/swift-semantic-adapter-terminal-correction.md").read_text()
        for text in ["contract-model checks", "no 32-word observation", "not implementation selection",
                     "No new error code", "no typed flag/debit is returned"]:
            self.assertIn(text,doc)

if __name__=="__main__":
    unittest.main(verbosity=2)
