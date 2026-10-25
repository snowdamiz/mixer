#!/usr/bin/env python3
"""Finite mocked independent-review guards. No file restoration, compiler, or guest execution."""
import copy
import unittest
from unittest.mock import patch
import packetlib as p


class ReviewGuardTests(unittest.TestCase):
    def fixture(self):
        review=p.ROOT/'verification/swift-cache-retention-review'
        selection={'reviewSealPath':str(review/'seal.json'), 'reviewSealSHA256':'seal',
                   'reviewSummaryPath':str(review/'result-summary.json'), 'reviewSummarySHA256':'summary'}
        summary={'schema':1,'status':'finite-correctness-accounting-prerequisite-accepted',
                 'finitePrerequisiteAccepted':True,'blockingFindings':[],
                 'candidateSealSHA256':p.CANDIDATE_SEAL,'candidateManifestSHA256':p.CANDIDATE_CLOSURE,
                 'baselineClosureSHA256':p.LIVE_BASELINE_CLOSURE,
                 'fullDiagnosticSelected':False,'liveIntegrationAccepted':False,'gaAccepted':False}
        seal={'schema':1,'sealedUTC':'2026-10-25T10:00:00+00:00',
              'members':{'result-summary.json':'summary'}, 'externalMembers':{}}
        return selection,summary,seal

    def run_guard(self,selection,summary,seal,sha_override=None):
        def digest(path):
            return (sha_override or {}).get(path.name, 'seal' if path.name=='seal.json' else 'summary')
        with patch.object(p,'sha',side_effect=digest),patch.object(p,'read',side_effect=lambda path:seal if path.name=='seal.json' else summary):
            return p.accepted_review(selection)

    def test_final_accepted_review_is_necessary_prerequisite_only(self):
        selection,summary,seal=self.fixture()
        self.assertEqual(self.run_guard(selection,summary,seal),summary)

    def test_rejected_or_unfinished_review_fails_closed(self):
        selection,summary,seal=self.fixture()
        for field,value in [('finitePrerequisiteAccepted',False),('status','under-review'),('blockingFindings',['blocking'])]:
            rejected=copy.deepcopy(summary);rejected[field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):
                self.run_guard(selection,rejected,seal)

    def test_candidate_and_baseline_cannot_be_substituted(self):
        selection,summary,seal=self.fixture()
        for field in ('candidateSealSHA256','candidateManifestSHA256','baselineClosureSHA256'):
            rejected=copy.deepcopy(summary);rejected[field]='other'
            with self.subTest(field=field),self.assertRaises(AssertionError):
                self.run_guard(selection,rejected,seal)

    def test_review_cannot_claim_target_integration_or_ga_selection(self):
        selection,summary,seal=self.fixture()
        for field in ('fullDiagnosticSelected','liveIntegrationAccepted','gaAccepted'):
            rejected=copy.deepcopy(summary);rejected[field]=True
            with self.subTest(field=field),self.assertRaises(AssertionError):
                self.run_guard(selection,rejected,seal)

    def test_unsealed_summary_fails_closed(self):
        selection,summary,seal=self.fixture();seal['members']={}
        with self.assertRaises(AssertionError):self.run_guard(selection,summary,seal)

    def test_review_hash_drift_fails_closed(self):
        selection,summary,seal=self.fixture()
        for name in ('seal.json','result-summary.json'):
            with self.subTest(name=name),self.assertRaises(AssertionError):
                self.run_guard(selection,summary,seal,{name:'drift'})

    def test_historical_or_alternate_review_path_fails_closed(self):
        selection,summary,seal=self.fixture();selection['reviewSealPath']='/oldpacket/seal.json'
        with self.assertRaises(AssertionError):self.run_guard(selection,summary,seal)

    def test_archive_names_are_closed_and_relative(self):
        for name in ('/absolute','../escape','a/../escape','./local','a//b',''):
            with self.subTest(name=name),self.assertRaises(AssertionError):p.safe_name(name)
        self.assertEqual(str(p.safe_name('src/file.rs')),'src/file.rs')


if __name__=='__main__':
    unittest.main(verbosity=2)
