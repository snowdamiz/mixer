"""Exercise local completion decisions and the independent review counterexamples."""

import copy
import json
from pathlib import Path
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = runpy.run_path(str(ROOT / 'scripts/check-plan-completion.py'))


class PlanCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = {
            name: json.loads((ROOT / name).read_text()) for name in VALIDATOR['INPUTS']
        }

    def completed(self):
        documents = copy.deepcopy(self.documents)
        for gate in documents['gates/local.json']['gates']:
            gate.update(status='passed', evidence=['fixture-receipt'], reviewer='fixture-reviewer')
        for milestone in documents['dogfood/receipts/milestones.json']['milestones']:
            local = milestone['localAcceptance']
            if local['requiredForPlanCompletion']:
                local.update(status='passed', evidence=['fixture-receipt'], reviewer='fixture-reviewer')
        documents['gates/local.json']['status'] = 'complete'
        return documents

    def test_current_plan_records_are_consistent(self):
        self.assertEqual(VALIDATOR['check_documents'](self.documents), [])

    def test_local_completion_does_not_wait_for_launch(self):
        documents = self.completed()
        for gate in documents['gates/ga.json']['gates']:
            gate.update(status='planned', evidence=[], reviewer=None)
        self.assertEqual(VALIDATOR['check_documents'](documents), [])

    def test_completion_rejects_each_unfinished_gate(self):
        for index in range(8):
            with self.subTest(gate=index):
                documents = self.completed()
                documents['gates/local.json']['gates'][index]['status'] = 'planned'
                self.assertTrue(VALIDATOR['check_documents'](documents))

    def test_pass_rejects_malformed_evidence_and_reviewer(self):
        changes = ({'evidence': [None]}, {'evidence': [' ']}, {'evidence': 'receipt'},
                   {'evidence': []}, {'reviewer': True}, {'reviewer': ' '}, {'reviewer': None})
        for kind in ('gate', 'milestone'):
            for change in changes:
                with self.subTest(kind=kind, change=change):
                    documents = self.completed()
                    record = (documents['gates/local.json']['gates'][0] if kind == 'gate'
                              else documents['dogfood/receipts/milestones.json']
                              ['milestones'][0]['localAcceptance'])
                    record.update(change)
                    self.assertTrue(VALIDATOR['check_documents'](documents))

    def test_packages_and_milestones_cannot_disappear(self):
        for name, key in (('work-graph.json', 'packages'),
                          ('dogfood/receipts/milestones.json', 'milestones')):
            for mutation in ('empty', 'missing', 'duplicate', 'reordered'):
                with self.subTest(name=name, mutation=mutation):
                    documents = self.completed()
                    records = documents[name][key]
                    if mutation == 'empty':
                        records.clear()
                    elif mutation == 'missing':
                        records.pop()
                    elif mutation == 'duplicate':
                        records.append(copy.deepcopy(records[0]))
                    else:
                        records.reverse()
                    self.assertTrue(VALIDATOR['check_documents'](documents))

    def test_fieldlog_gate_requires_each_local_milestone(self):
        for index in (*range(7), 8):
            with self.subTest(milestone=index):
                documents = self.completed()
                documents['dogfood/receipts/milestones.json']['milestones'][index][
                    'localAcceptance']['status'] = 'planned'
                self.assertTrue(VALIDATOR['check_documents'](documents))


if __name__ == '__main__':
    unittest.main()
