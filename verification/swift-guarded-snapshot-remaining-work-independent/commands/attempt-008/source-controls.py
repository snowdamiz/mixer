#!/usr/bin/env python3
"""Independent adversarial callers of the frozen candidate API; no mutations."""
import copy
import json
from pathlib import Path
import sys
import unittest

D = Path(__file__).resolve().parent
R = D.parents[1]
sys.path.insert(0, str(R / "verification/swift-guarded-snapshot-remaining-work-interfaces"))
from composer import Context, Refused, SyntheticInputs, bind, context, evaluate_synthetic

adverse = []

class IndependentControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = context()
        cls.original, cls.direct, cls.proposal = cls.ctx.original, cls.ctx.direct, cls.ctx.expected_proposal
        cls.bound = bind(cls.original,cls.direct,cls.proposal,mode="conditional-review-candidate",ctx=cls.ctx)

    def reject(self,label,call):
        with self.assertRaises(Refused,msg=label):
            call()
        adverse.append(label)

    def inputs(self):
        return {k:7 for k in self.bound["remaining_symbols"]}

    def candidate(self,proposal):
        return bind(self.original,self.direct,proposal,mode="conditional-review-candidate",ctx=self.ctx)

    def test_coverage_and_resource_dispositions_cannot_be_repriced(self):
        for i in range(14):
            for price in (0,1,193,2**64-1):
                p = copy.deepcopy(self.proposal)
                if i < 12:
                    p["callee_boundary_rows"][i]["numeric_private_price_assigned"] = price
                else:
                    p["whole_leaf_boundary_rows"][i-12]["additional_price_assigned"] = price
                self.reject(f"boundary-reprice:{i}:{price}",lambda p=p:self.candidate(p))
        for key in ("typed_payload_multiplicities","authored_callback_multiplicities","primitive_event_multiplicities","accepted_named_row_multiplicities"):
            for i in range(12):
                p = copy.deepcopy(self.proposal)
                p["callee_boundary_rows"][i][key] = {}
                if p == self.proposal:
                    continue
                self.reject(f"coverage-erasure:{i}:{key}",lambda p=p:self.candidate(p))

    def test_each_allocation_native_field_and_request_event_is_mandatory(self):
        for i,row in enumerate(self.proposal["constructor_allocation_requests"]):
            for key in row["native_fields"]:
                for value in (0,True,False):
                    p=copy.deepcopy(self.proposal);p["constructor_allocation_requests"][i]["native_fields"][key]=value
                    self.reject(f"native-request:{i}:{key}:{value!r}",lambda p=p:self.candidate(p))
            for key in ("max_calls","logical_interface_events"):
                p=copy.deepcopy(self.proposal);p["constructor_allocation_requests"][i][key]=True
                self.reject(f"bool-for-integer-one:{i}:{key}",lambda p=p:self.candidate(p))
        for value in (0,55380,55382,110762):
            p=copy.deepcopy(self.proposal);p["constructor_allocation_supplement"]=value
            self.reject(f"supplement-missing-or-double:{value}",lambda p=p:self.candidate(p))

    def test_context_original_receipt_unit_and_scope_are_exact(self):
        for field in ("schema","source_tree_sha256","host_tree_sha256","unit","operational_grant"):
            old=copy.deepcopy(self.original)
            old[field]=True if field=="schema" else "foreign"
            ctx=Context(old,self.direct,self.proposal,{})
            self.reject("forged-context:"+field,lambda old=old,ctx=ctx:bind(old,self.direct,self.proposal,mode="conditional-review-candidate",ctx=ctx))
        for i,row in enumerate(self.direct["exact_export_scope"]):
            d=copy.deepcopy(self.direct);d["exact_export_scope"][i]["fixed_event_already_charged"]=True
            self.reject(f"direct-bool-event:{i}",lambda d=d:bind(self.original,d,ctx=self.ctx))
        for i in range(14):
            p=copy.deepcopy(self.proposal);p["exact_proposed_symbol_scope"].pop(i)
            self.reject(f"scope-omission:{i}",lambda p=p:self.candidate(p))
        for p in (None,{},dict(self.proposal,root_selected=True),dict(self.proposal,operational_grant=True)):
            self.reject("unbound-or-granting-proposal:"+str(p is None),lambda p=p:self.candidate(p))

    def test_atomic_callback_split_and_payload_mutations_refuse(self):
        for value in (False,True,0,2,"unbounded"):
            p=copy.deepcopy(self.proposal);p["logical_atomic_callback"]["count"]=value
            self.reject("atomic-count:"+repr(value),lambda p=p:self.candidate(p))
        p=copy.deepcopy(self.proposal);p["logical_atomic_callback"]["dynamic_retry_or_CPU_claim"]=True
        self.reject("atomic-CPU-escalation",lambda:self.candidate(p))
        for node in ("core_before_fixed_store","core_fixed_store_and_after"):
            p=copy.deepcopy(self.proposal)
            row=next(r for r in p["callee_boundary_rows"] if r["node"]==node)
            row["visited_node_multiplicities"]={}
            self.reject("phase-coverage-omission:"+node,lambda p=p:self.candidate(p))

    def test_every_external_input_required_and_numeric_types_checked(self):
        for key,row in self.bound["remaining_symbols"].items():
            values=self.inputs();del values[key]
            self.reject("required:"+key,lambda values=values:evaluate_synthetic(self.bound,SyntheticInputs(values,"independent-control"),ctx=self.ctx))
            for bad in (True,False,-1,1.0,"1",None,2**64):
                values=self.inputs();values[key]=bad
                self.reject("invalid:"+key+":"+repr(bad),lambda values=values:evaluate_synthetic(self.bound,SyntheticInputs(values,"independent-control"),ctx=self.ctx))
            if row["positive"]:
                values=self.inputs();values[key]=0
                self.reject("zero-positive:"+key,lambda values=values:evaluate_synthetic(self.bound,SyntheticInputs(values,"independent-control"),ctx=self.ctx))
        values=self.inputs();values["private_price"]=0
        self.reject("extra-private-price",lambda:evaluate_synthetic(self.bound,SyntheticInputs(values,"independent-control"),ctx=self.ctx))

    def test_outputs_stay_synthetic_and_cannot_grant(self):
        values=self.inputs()
        result=evaluate_synthetic(self.bound,SyntheticInputs(values,"independent-synthetic-arithmetic"),ctx=self.ctx)
        independent=895084428323053276+sum(n*values[k] for k,n in self.bound["whole_host"]["terms"].items())
        self.assertEqual(result["whole_host"],independent)
        for key in ("accepted_bound","operational_grant","root_policy_selected","native_or_GA"):
            self.assertIs(result[key],False)
            bad=copy.deepcopy(self.bound);bad[key]=True
            self.reject("authority-tamper:"+key,lambda bad=bad:evaluate_synthetic(bad,SyntheticInputs(values,"independent-control"),ctx=self.ctx))
        for phase in self.bound["child"]:
            bad=copy.deepcopy(self.bound);bad["child"][phase]["fixed"]+=55381
            self.reject("duplicate-or-misplaced-supplement:"+phase,lambda bad=bad:evaluate_synthetic(bad,SyntheticInputs(values,"independent-control"),ctx=self.ctx))
        for mode in ("accepted-bound","operational","selected","root-selected"):
            self.reject("forbidden-mode:"+mode,lambda mode=mode:bind(self.original,self.direct,self.proposal,mode=mode,ctx=self.ctx))

if __name__ == "__main__":
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls))
    output={"schema":1,"test_methods":result.testsRun,"adverse_cases":len(adverse),"adverse_case_names":adverse,"failures":len(result.failures),"errors":len(result.errors),"passed":result.wasSuccessful(),"scope":"independent adversarial callers against the frozen candidate composer; arithmetic synthetic only","accepted_bound":False,"operational_grant":False}
    data=(json.dumps(output,indent=2,sort_keys=True)+"\n").encode()
    if "--check" in sys.argv:
        if (D/"controls.json").read_bytes()!=data:raise AssertionError("changed-independent-controls")
    else:
        if (D/"seal.json").exists():raise AssertionError("frozen-independent-review")
        (D/"controls.json").write_bytes(data)
    print(json.dumps({k:output[k] for k in ("test_methods","adverse_cases","failures","errors","passed")}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
