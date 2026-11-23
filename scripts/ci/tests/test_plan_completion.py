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
        pivot = documents['work-graph.json']['uiPlatformPivot']
        for record in (*pivot['steps'], *pivot['spikes'], pivot['finalReplay']):
            record.update(state='passed', evidence=['fixture-receipt'], reviewer='fixture-reviewer')
        for spike in pivot['spikes']:
            spike['outcome'] = 'fixture-outcome'
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

    def test_pivot_record_is_required(self):
        documents = self.completed()
        del documents['work-graph.json']['uiPlatformPivot']
        self.assertTrue(VALIDATOR['check_documents'](documents))

    def test_completion_rejects_each_unfinished_pivot_step(self):
        for index in range(6):
            with self.subTest(step=index):
                documents = self.completed()
                documents['work-graph.json']['uiPlatformPivot']['steps'][index]['state'] = 'running'
                self.assertTrue(VALIDATOR['check_documents'](documents))

    def test_pivot_results_require_evidence_and_outcome(self):
        for change in ({'state': 'passed', 'evidence': [], 'reviewer': None}, {'state': 'failed', 'outcome': None},
                       {'outcome': None}, {'outcome': ' '}):
            with self.subTest(change=change):
                documents = self.completed()
                documents['work-graph.json']['uiPlatformPivot']['spikes'][0].update(change)
                self.assertTrue(VALIDATOR['check_documents'](documents))

    def test_pivot_step_requires_its_prerequisites(self):
        cases = ((('spikes', 6), "UP4: passed before ['S5']"), (('spikes', 1), "UP5: passed before ['S2a']"),
                 (('spikes', 2), "UP5: passed before ['S2b']"), (('spikes', 3), "UP5: passed before ['S3n']"),
                 (('spikes', 4), "UP5: passed before ['S3g']"), (('spikes', 5), "UP5: passed before ['S4']"),
                 (('steps', 1), "UP4: passed before ['UP2']"), (('finalReplay', None), "UP6: passed before ['finalReplay']"))
        for (key, index), message in cases:
            with self.subTest(record=(key, index)):
                documents = self.completed()
                pivot = documents['work-graph.json']['uiPlatformPivot']
                (pivot[key] if index is None else pivot[key][index])['state'] = 'running'
                self.assertIn(message, VALIDATOR['check_documents'](documents))

    def test_auxiliary_pivot_records_keep_their_ids(self):
        documents = self.completed()
        pivot = documents['work-graph.json']['uiPlatformPivot']
        pivot['finalReplay']['id'] = 'UP6'
        self.assertIn('finalReplay: pivot record id must be finalReplay', VALIDATOR['check_documents'](documents))

    def test_uplift_needs_every_spike_settled(self):
        documents = self.completed()
        documents['work-graph.json']['uiPlatformPivot']['spikes'][2].update(state='planned', outcome=None)
        self.assertIn('UP3: passed before every spike settled', VALIDATOR['check_documents'](documents))

    def test_update_guests_need_a_settled_module_name(self):
        documents = self.completed()
        spike = documents['work-graph.json']['uiPlatformPivot']['spikes'][0]
        spike.update(state='running', outcome=None)
        self.assertIn('UP5: passed before S1 settled', VALIDATOR['check_documents'](documents))
        spike.update(state='failed', outcome='Shared modules import MixerSwiftUI explicitly')
        self.assertEqual(VALIDATOR['check_documents'](documents), [])

    def test_fieldlog_gates_wait_for_the_final_replay(self):
        for record in ('UP6', 'finalReplay'):
            for gate, other in ((1, 7), (7, 1)):
                with self.subTest(record=record, gate=gate):
                    documents = self.completed()
                    documents['gates/local.json']['status'] = 'in_progress'
                    documents['gates/local.json']['gates'][other]['status'] = 'running'
                    pivot = documents['work-graph.json']['uiPlatformPivot']
                    target = pivot['finalReplay'] if record == 'finalReplay' else pivot['steps'][5]
                    target['state'] = 'running'
                    self.assertIn('L02 and L08 pass only after UP6 and the final replay', VALIDATOR['check_documents'](documents))
                    target['state'] = 'passed'
                    self.assertEqual(VALIDATOR['check_documents'](documents), [])

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
