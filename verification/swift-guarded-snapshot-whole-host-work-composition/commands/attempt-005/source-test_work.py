#!/usr/bin/env python3
"""Independent finite arithmetic and adverse controls; no source/runtime run."""
import copy, json, random, unittest
from pathlib import Path
from model import U64, PHASES, Refused, Linear, SyntheticAssumptions, RetentionModel, add, mul, total, evaluate_synthetic, qualification
D=Path(__file__).resolve().parent
def load(name):return json.loads((D/name).read_text())

class WorkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.interface=load('work-interface.json')
    def values(self):return {k:(2 if not v['positive'] else 7) for k,v in self.interface['symbols'].items()}
    def evaluate(self,values=None,interface=None):
        return evaluate_synthetic(interface or self.interface,SyntheticAssumptions(values or self.values(),'explicit-test-only'))

    def test_checked_add_multiply_boundaries(self):
        for value in [0,1,U64//2,U64-1,U64]:
            self.assertEqual(add(value,0),value);self.assertEqual(mul(value,1),value)
        for values in [(U64,1),(U64-1,2)]:
            with self.assertRaises(Refused):add(*values)
        with self.assertRaises(Refused):mul(U64,2)
        for value in [True,False,None,-1,1.0,'1',U64+1]:
            with self.assertRaises(Refused):add(value)
            with self.assertRaises(Refused):mul(value,1)

    def test_every_required_symbol_omission_zero_and_type(self):
        for key,definition in self.interface['symbols'].items():
            values=self.values();del values[key]
            with self.subTest(key=key,case='omitted'):
                with self.assertRaises(Refused):self.evaluate(values)
            for value in [None,-1,True,1.0,U64+1]:
                values=self.values();values[key]=value
                with self.subTest(key=key,value=value):
                    with self.assertRaises(Refused):self.evaluate(values)
            values=self.values();values[key]=0
            if definition['positive']:
                with self.subTest(key=key,case='zero'):
                    with self.assertRaises(Refused):self.evaluate(values)
            else:self.assertFalse(self.evaluate(values)['accepted_bound'])

    def test_unknown_input_and_no_implicit_context(self):
        values=self.values();values['fallback']=1
        with self.assertRaises(Refused):self.evaluate(values)
        with self.assertRaises(Refused):evaluate_synthetic(self.interface,self.values())
        with self.assertRaises(Refused):evaluate_synthetic(self.interface,SyntheticAssumptions(self.values(),''))

    def test_all_six_components_required_in_source_order(self):
        self.assertEqual(tuple(self.interface['child']),PHASES)
        for phase in PHASES:
            changed=copy.deepcopy(self.interface);del changed['child'][phase]
            with self.assertRaises(Refused):self.evaluate(interface=changed)
            changed=copy.deepcopy(self.interface);changed['child'][phase]={'fixed':0,'terms':{}}
            with self.assertRaises(Refused):self.evaluate(interface=changed)
        changed=copy.deepcopy(self.interface);changed['child']=dict(reversed(list(changed['child'].items())))
        with self.assertRaises(Refused):self.evaluate(interface=changed)

    def test_no_saturating_math_or_whole_sum_omission(self):
        changed=copy.deepcopy(self.interface);changed['whole_host']['fixed']-=1
        with self.assertRaises(Refused):self.evaluate(interface=changed)
        values=self.values();values['L_str']=U64
        with self.assertRaises(Refused):self.evaluate(values)
        for key in ['P0_inspections','P0_usage_reads']:
            values=self.values();values[key]=U64
            with self.assertRaises(Refused):self.evaluate(values)

    def test_independent_integer_oracle(self):
        rng=random.Random(146)
        for _ in range(128):
            values={k:rng.randrange(1,100000) for k in self.interface['symbols']}
            result=self.evaluate(values)
            calc=lambda e:e['fixed']+sum(v*values[k] for k,v in e['terms'].items())
            self.assertEqual(result['whole_host'],calc(self.interface['P0'])+sum(map(calc,self.interface['child'].values())))
            self.assertEqual(result['whole_host'],calc(self.interface['whole_host']))
            self.assertFalse(result['operational_grant'])

    def test_exact_33_edges_21_private_and19_payloads(self):
        edges=load('actual-edges.json');imports=load('typed-callee-imports.json');private=load('private-export-allowance-roster.json')
        self.assertEqual(len(edges['33cut_occurrences']),33);self.assertEqual(imports['private_allowances'],21)
        self.assertEqual(len(imports['typed_imports']),19);self.assertEqual(private['count'],21)
        self.assertTrue(all(x['mandatory_symbol_preserved'] and not x['closed_by_this_packet'] for x in private['exports']))
        self.assertEqual(edges['shell_fixed'],4236953);self.assertEqual(edges['shell_L_str_coefficient'],4376)
        self.assertEqual(edges['product_aggregate_credit'],0)

    def test_constructor_real_typed_destructors_not_logical_credit(self):
        imports=load('typed-callee-imports.json');decoded=load('additive-decoded-function-row.json')
        proof=imports['typed_imports']['payload::AdoptedProof']
        self.assertEqual(imports['constructor_subset'],134288951629)
        self.assertEqual(imports['constructor_exact_payload'],134288951629+2*proof)
        self.assertEqual(imports['extra_AdoptedProof_visits'],2)
        self.assertEqual(decoded['row']['inline_bytes'],96)
        self.assertEqual(set(decoded['row']['resource_frontiers']),{'Vec<Type>','Vec<DecodedInstruction>','Vec<u32>'})
        self.assertGreater(decoded['price'],96)

    def test_entry53_applied_once_and_P5_carrier_separate(self):
        entry=load('entry-partition.json')
        self.assertEqual(entry['source_total'],119922);self.assertEqual(entry['carrier_source_total'],92906)
        self.assertEqual(entry['setup_drop_visits']+entry['caller_drop_visits'],53)
        self.assertEqual(entry['total_drop_work'],53*1210256815)
        self.assertEqual(entry['returned_P5_payload'],45196204)
        self.assertTrue(entry['returned_carrier_events_separate'])
        self.assertTrue(any(x['phase']=='P5_payload_teardown' and 'OwnedFixtureOutcomeV1::' in x['statement'] for x in entry['statement_partition']))

    def test_prestore_and_after_store_are_distinct(self):
        edges=load('actual-edges.json')['edges']
        for key,phase in [('core_before_fixed_store','P3_before_store'),('core_fixed_store_and_after','P4_selected_route')]:
            selected=[x for x in edges if x['key']==key]
            self.assertEqual(len(selected),1);self.assertEqual(selected[0]['phase'],phase)
        self.assertFalse(self.interface['product451814442_aggregate_credit'])

    def test_array_source_scope_and_strings_unresolved(self):
        values=load('unsized-provenance.json')
        self.assertEqual(values['array']['count'],4);self.assertEqual(values['array']['L'],112)
        self.assertEqual(values['array']['scope'],'only AccountedWasi::snapshot_pair_v1')
        self.assertEqual(values['str']['status'],'unresolved-required');self.assertIn('L_str',self.interface['symbols'])

    def test_loader_cap_and_actual_fixture_are_separate(self):
        values=load('loader-geometries.json');cap=values['accepted_cap_bound']
        self.assertEqual(cap['wrapper'],97394558768720);self.assertEqual(cap['K'],1748020339)
        self.assertEqual(cap['work'],cap['wrapper']+(512000000+1)*cap['K'])
        self.assertEqual(values['original_selected_validation_limits']['work_credits'],1000000)
        self.assertEqual(values['actual_source_selection']['bytes'],1947)
        self.assertFalse(values['actual_fixture_loader_work_selected'])

    def test_P0_count_coefficients_and_no_policy_minted(self):
        expression=self.interface['P0'];self.assertEqual(expression['fixed'],2628088)
        self.assertEqual(expression['terms']['P0_inspections'],194231);self.assertEqual(expression['terms']['P0_usage_reads'],1039)
        q=qualification(self.interface);self.assertFalse(q['complete_host_funding']);self.assertFalse(q['operational_grant'])
        self.assertGreater(len(q['missing']),0)

    def test_reservation_precedes_any_action_and_dispatch_once(self):
        for funded in [False,True]:
            account=RetentionModel(funded,100,200)
            with self.assertRaises(Refused):account.dispatch()
            if not funded:
                with self.assertRaises(Refused):account.commit()
                self.assertEqual(account.work_consumed,0)
            else:
                account.commit();self.assertEqual(account.storage_retained,200)
                account.dispatch()
                with self.assertRaises(Refused):account.dispatch()
                with self.assertRaises(Refused):account.commit()

    def test_retention_through_destroy_token_and_late_P0_release(self):
        account=RetentionModel(True,100,200);account.commit();account.dispatch()
        with self.assertRaises(Refused):account.release()
        account.destroy();self.assertEqual(account.storage_retained,200)
        self.assertTrue(account.token_returned);account.release()
        self.assertEqual(account.storage_retained,0);self.assertEqual(account.work_consumed,100)
        with self.assertRaises(Refused):account.release()

    def test_unwind_or_unused_ticket_preserves_charge(self):
        account=RetentionModel(True,100,200);account.commit()
        with self.assertRaises(Refused):account.release()
        self.assertEqual(account.storage_retained,200)
        account.dispatch();account.destroy(completes=False)
        with self.assertRaises(Refused):account.release()
        self.assertEqual(account.work_consumed,100);self.assertEqual(account.storage_retained,200)

    def test_linear_rejects_duplicate_negative_bool(self):
        for expression in [(1,(('x',1),('x',2))),(-1,()),(True,()),(0,(('x',0),))]:
            with self.assertRaises(Refused):Linear(*expression)
        self.assertEqual(total([Linear(3),Linear(5)]).fixed,8)

if __name__=='__main__':unittest.main(verbosity=2)
