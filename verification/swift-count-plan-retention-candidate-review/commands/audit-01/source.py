#!/usr/bin/env python3
"""Independent, read-only audit of the rejected finite Rust result packet.

No producer program, archived source, compiler, native runtime or hosted harness
is executed. Archive members remain in memory. Outputs are owned review files.
"""
import ast
import collections
import datetime
import difflib
import hashlib
import json
import pathlib
import platform
import re
import subprocess
import sys
import tarfile
import unittest

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PRODUCER = ROOT / 'verification/swift-count-plan-retention-candidate'
SEAL_SHA = '29601717bcdc4c8a6c1de9c80ab2d26fdcc04c265b799dfa7e07868d541eb8a1'
LIVE_SHA = '16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
REPORT = {}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def js(path):
    return json.loads(path.read_bytes())

def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()

def raw(name, stream='stdout'):
    return (PRODUCER / 'commands' / name / stream).read_text()

def records(text, prefix):
    # A libtest method prefix may precede the first instrumented record.
    return [line[line.index(prefix):] for line in text.splitlines() if prefix in line]

def json_records(text, prefix):
    return [json.loads(line[len(prefix):]) for line in records(text, prefix)]

def traces(name):
    return {r['case']: r for r in json_records(raw(name), 'COST_TRACE ')}

def archives():
    result = {}
    for name in ['baseline', 'tested-baseline', 'candidate']:
        with tarfile.open(PRODUCER / (name + '-source.tar.gz')) as archive:
            members = archive.getmembers()
            assert len(members) == 132
            assert len({m.name for m in members}) == 132
            assert all(m.isfile() and not pathlib.PurePosixPath(m.name).is_absolute()
                       and '..' not in pathlib.PurePosixPath(m.name).parts for m in members)
            result[name] = {m.name: archive.extractfile(m).read() for m in members}
    return result

ARCHIVES = archives()
B = raw('baseline-expanded-2')
C = raw('candidate-expanded')

class ResultAudit(unittest.TestCase):
    def test_01_exact_producer_seal_and_members(self):
        self.assertEqual(digest((PRODUCER / 'seal.json').read_bytes()), SEAL_SHA)
        seal = js(PRODUCER / 'seal.json')
        self.assertEqual(len(seal['members']), 114)
        self.assertEqual(len({m['path'] for m in seal['members']}), 114)
        for member in seal['members']:
            path = ROOT / member['path']
            self.assertTrue(path.is_file() and not path.is_symlink(), member['path'])
            data = path.read_bytes()
            self.assertEqual(len(data), member['bytes'], member['path'])
            self.assertEqual(digest(data), member['sha256'], member['path'])
        REPORT['producerSeal'] = {'sha256': SEAL_SHA, 'members': 114}

    def test_02_archives_exactly_match_all_three_manifests(self):
        summary = {}
        for name, files in ARCHIVES.items():
            manifest_path = PRODUCER / (name + '-source-manifest.json')
            manifest = js(manifest_path)
            self.assertEqual({p: digest(b) for p, b in files.items()}, manifest)
            self.assertEqual(len(manifest), 132)
            summary[name] = {'files': 132, 'manifestSHA256': digest(manifest_path.read_bytes()),
                             'archiveSHA256': digest((PRODUCER / (name + '-source.tar.gz')).read_bytes())}
        self.assertEqual(summary['baseline']['manifestSHA256'], LIVE_SHA)
        REPORT['archives'] = summary

    def test_03_live_exact_132_name_closure_is_pristine(self):
        manifest = js(PRODUCER / 'baseline-source-manifest.json')
        observed = {name: digest((ROOT / 'vm' / name).read_bytes()) for name in manifest}
        self.assertEqual(observed, manifest)
        self.assertEqual(digest(canonical(observed)), LIVE_SHA)
        REPORT['liveSource'] = {'fileCount': 132, 'closureSHA256': LIVE_SHA,
                                'scope': 'Exact named closure; not a claim about every unlisted workspace file'}

    def test_04_both_patches_are_exact_archive_diffs(self):
        changes = {}
        for before, patch in [('baseline', 'candidate-vs-pristine.patch'),
                              ('tested-baseline', 'candidate-vs-tested-baseline.patch')]:
            generated = ''
            names = []
            for name in sorted(ARCHIVES[before]):
                old, new = ARCHIVES[before][name], ARCHIVES['candidate'][name]
                if old != new:
                    names.append(name)
                    generated += ''.join(difflib.unified_diff(old.decode().splitlines(True), new.decode().splitlines(True),
                                                             fromfile='a/' + name, tofile='b/' + name))
            self.assertEqual(generated.encode(), (PRODUCER / patch).read_bytes())
            changes[patch] = names
        self.assertEqual(len(changes['candidate-vs-tested-baseline.patch']), 4)
        REPORT['patchChanges'] = changes

    def test_05_fourteen_receipts_bind_streams_source_and_tools(self):
        receipt = js(PRODUCER / 'receipt.json')
        commands = sorted((PRODUCER / 'commands').iterdir())
        self.assertEqual(len(commands), 14)
        self.assertEqual({p.name for p in commands}, set(receipt['commands']))
        summary = {}
        for directory in commands:
            command, result = js(directory / 'command.json'), js(directory / 'result.json')
            binding = receipt['commands'][directory.name]
            self.assertEqual(digest((directory / 'result.json').read_bytes()), binding['resultSHA256'])
            self.assertEqual(command['sourceManifestSHA256'], digest((directory / 'source-manifest.json').read_bytes()))
            self.assertEqual(command['sourceManifestSHA256'], binding['sourceManifestSHA256'])
            self.assertEqual(result['exitCode'], binding['exitCode'])
            self.assertTrue(result['sourceUnchanged'])
            self.assertEqual(command['liveClosureBefore'], LIVE_SHA)
            self.assertEqual(result['liveClosureAfter'], LIVE_SHA)
            self.assertIsNone(result['error'])
            self.assertIn('--offline', command['argv'])
            self.assertEqual(command['environmentOverrides']['CARGO_NET_OFFLINE'], 'true')
            self.assertEqual(command['environmentOverrides']['CARGO_BUILD_JOBS'], '1')
            for stream in ['stdout', 'stderr']:
                data = (directory / stream).read_bytes()
                self.assertEqual(digest(data), result[stream + 'SHA256'])
                self.assertEqual(len(data), result[stream + 'Bytes'])
            for tool, version in [('cargo', 'cargo 1.99.0'), ('rustc', 'rustc 1.99.0')]:
                self.assertTrue(command['tools'][tool]['version'].startswith(version))
                self.assertRegex(command['tools'][tool]['sha256'], r'^[0-9a-f]{64}$')
            summary[directory.name] = {'exitCode': result['exitCode'], 'sourceManifestSHA256': command['sourceManifestSHA256'],
                                       'testResults': re.findall(r'test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed;', raw(directory.name))}
        self.assertEqual([n for n in summary if summary[n]['exitCode'] != 0],
                         ['baseline-expanded', 'candidate-original-swift', 'candidate-original-swift-2'])
        REPORT['producerCommands'] = summary

    def test_06_original_suite_failures_remain_separate(self):
        self.assertIn('39 passed; 0 failed;', raw('baseline-original-swift'))
        self.assertIn('37 passed; 2 failed;', raw('candidate-original-swift-2'))
        err = raw('candidate-original-swift-2', 'stderr')
        self.assertIn('cache_tests::plan_reuse_observation', err)
        self.assertIn('left: 225\n right: 288', err)
        self.assertIn('cache_tests::reset_elision_observation_fixture', err)
        self.assertIn('left: 0\n right: 5027', err)
        old = ARCHIVES['baseline']['src/experimental_swift_reactor/cache_tests.rs'].decode()
        new = ARCHIVES['candidate']['src/experimental_swift_reactor/cache_tests.rs'].decode()
        # All original tests are byte-preserved except this added passive hook.
        original_prefix = new[:new.index('\n// Fresh finite traces run unchanged')]
        self.assertEqual(original_prefix.replace('    count_candidate_checkpoint(control);\n', ''), old)
        REPORT['originalSwift'] = {'baseline': {'passed': 39, 'failed': 0}, 'candidate': {'passed': 37, 'failed': 2},
                                    'cleanupCaveat': 'Two retained assertion panics precede consuming finish; no zero-ledger claim for them'}

    def test_07_compile_failures_are_preserved_and_adapters_narrow(self):
        self.assertIn('no method named `test_changed_instructions`', raw('candidate-original-swift', 'stderr'))
        self.assertIn('SwiftRunFailureKind::AllPinned', raw('baseline-expanded', 'stderr'))
        patch = (PRODUCER / 'candidate-vs-tested-baseline.patch').read_text()
        self.assertIn('-            counts.test_changed_instructions(),', patch)
        self.assertIn('+            SwiftMode::scan_counts(&counts).test_changed_instructions(),', patch)
        self.assertFalse(js(PRODUCER / 'test-adapter-correction.json')['existingAssertionRemoved'])
        self.assertEqual(js(PRODUCER / 'probe-corrections.json')[0]['productionPolicyChanged'], False)

    def test_08_generic_and_new_and_common_counts_are_not_conflated(self):
        for side in ['baseline', 'candidate']:
            self.assertIn('5 passed; 0 failed;', raw(side + '-generic-unit'))
            s = raw(side + '-generic-integration')
            self.assertIn('9 passed; 0 failed;', s)
            self.assertIn('1 passed; 0 failed;', s)
            self.assertIn('3 passed; 0 failed;', raw(side + '-common'))
        self.assertIn('8 passed; 0 failed;', B)
        self.assertIn('9 passed; 0 failed;', C)
        REPORT['methodCounts'] = {'genericPrivateEach': 5, 'genericPublicEach': 9, 'genericAllocationEach': 1,
                                  'newBaseline': 8, 'newCandidate': 9, 'unchangedCommonEach': 3,
                                  'prospectiveLayoutCommands': 2}

    def test_09_generic_109_records_recomputed_from_raw_streams(self):
        left, right = records(B, 'GENERIC_'), records(C, 'GENERIC_')
        self.assertEqual(left, right)
        self.assertEqual(len(left), 109)
        d = js(PRODUCER / 'generic-differential.json')
        self.assertEqual(digest(('\n'.join(left) + '\n').encode()), d['baselineSHA256'])
        self.assertEqual(d['baselineSHA256'], d['candidateSHA256'])
        counts = collections.Counter(line.split()[0] for line in left)
        self.assertEqual(dict(counts), {'GENERIC_LAYOUT': 1, 'GENERIC_ACCESS': 6, 'GENERIC_STATE': 6,
                                       'GENERIC_PREFIX': 94, 'GENERIC_CANCEL': 2})
        REPORT['genericDifferential'] = {'records': 109, 'sha256': d['baselineSHA256'], 'kinds': dict(counts)}

    def test_10_six_raw_work_traces_and_historical_baseline(self):
        expected = {'hot16_scan128_four_rounds': (1558624, 1461008), 'cyclic65_three_rounds': (406583, 303416),
                    'expensive_hot_cheap_cold': (248012, 150228), 'cheap_hot_expensive_cold': (1444044, 1460948),
                    'uniform_hot_cold': (222412, 232148), 'expensive_old_to_cheap_cycle64_phase_shift': (17440, 25918)}
        left, right = traces('baseline-common'), traces('candidate-common')
        comparison = js(PRODUCER / 'comparison.json')
        historical = ROOT / comparison['historicalBaselineExactlyReproduced']['path']
        self.assertEqual(digest(historical.read_bytes()), comparison['historicalBaselineExactlyReproduced']['sha256'])
        self.assertEqual(left, {r['case']: r for r in json_records(historical.read_text(), 'COST_TRACE ')})
        self.assertEqual(set(left), set(expected)); self.assertEqual(set(right), set(expected))
        rows = []
        for case, pair in expected.items():
            self.assertEqual((left[case]['traceWork'], right[case]['traceWork']), pair)
            warm = 0 if case == 'cyclic65_three_rounds' else 16
            row = next(r for r in comparison['actualEngineRows'] if r['case'] == case)
            self.assertEqual(row['baseline'], left[case]); self.assertEqual(row['candidate'], right[case])
            self.assertEqual(row['intervalBaselineDecodes'], left[case]['decodes'] - warm)
            self.assertEqual(row['intervalCandidateDecodes'], right[case]['decodes'] - warm)
            self.assertEqual(row['deltaWork'], pair[1] - pair[0])
            for mode in [left, right]:
                self.assertEqual(mode[case]['instructions'], 0)
                self.assertEqual(mode[case]['peakTickets'], 73)
            rows.append({'case': case, 'baselineWork': pair[0], 'candidateWork': pair[1],
                         'deltaWork': pair[1] - pair[0], 'baselineIntervalDecodes': row['intervalBaselineDecodes'],
                         'candidateIntervalDecodes': row['intervalCandidateDecodes']})
        self.assertEqual(sum(r['deltaWork'] > 0 for r in rows), 3)
        REPORT['workTraces'] = rows

    def test_11_work_schedule_exact_added_57_and_no_hit_debit(self):
        for old, new in zip(records(B, 'COUNT_PREFIX '), records(C, 'COUNT_PREFIX ')):
            self.assertEqual(int(re.search(r'work=(\d+)', new)[1]) - int(re.search(r'work=(\d+)', old)[1]), 57)
        self.assertIn('shorter_work=204 ', B); self.assertIn('shorter_work=261 ', C)
        selection = js(PRODUCER / 'root-selection.json')
        self.assertEqual(selection['debits'], [41, 16])
        self.assertEqual(digest((PRODUCER / 'proposed-seam.md').read_bytes()), selection['proposalSHA256'])
        REPORT['workSchedule'] = {'missAdded': 57, 'blocks': [41, 16], 'hitAdded': 0,
                                  'units': 'Source-policy credits; not CPU, instructions, stack, memcpy or RSS'}

    def test_12_inventory_fields_nonoverlap_complete_results_and_padding(self):
        d = js(PRODUCER / 'inventory-fields.json')
        fields = json_records(C, 'COUNT_FIELD ')
        self.assertEqual(fields, d['fields']); self.assertEqual(len(fields), 25)
        occupied = []
        for field in fields:
            occupied.extend(range(field['offset'], field['offset'] + field['bytes']))
        self.assertEqual(len(occupied), len(set(occupied)))
        self.assertEqual(len(occupied), 6820); self.assertEqual(max(occupied), 6819)
        self.assertEqual(3*32 + 3*1096 + 2*8 + 3*8 + 4 + 4*8 + 3*24 + 3*1096, 6820)
        self.assertEqual(((6820 + 7)//8)*8, 6824); self.assertEqual(3*6824, 20472)
        for field in fields:
            if field['name'].startswith(('result_', 'preparation_')):
                self.assertEqual(field['bytes'], 1096)
        implemented = json_records(C, 'COUNT_IMPLEMENTED ')[0]
        self.assertEqual(implemented, {'outcome':32, 'result':1096, 'inventory':6824, 'threeInventories':20472,
                                      'operation':112822, 'persistentPolicyBytes':0, 'newTickets':0})
        REPORT['inventory'] = {'fields':25, 'namedBytes':6820, 'paddingBytes':4, 'bytes':6824, 'copies':3,
                               'dedicatedBytes':20472, 'outcomeBytes':32, 'resultBytes':1096}

    def test_13_delta_existing_zero_and_constructor_shape(self):
        old = ast.literal_eval(records(B, 'COUNT_SHAPE ')[0][len('COUNT_SHAPE '):])
        new = ast.literal_eval(records(C, 'COUNT_SHAPE ')[0][len('COUNT_SHAPE '):])
        self.assertEqual(old, [1304,760,976,296,184,136,120,92128,61880,92350,62888,1096])
        self.assertEqual(new, old[:9] + [112822] + old[10:])
        for side in ['baseline', 'candidate']:
            shape = json_records(raw(side + '-common'), 'COST_SHAPE ')[0]
            self.assertEqual(shape['constructorWork'], 4928)
            self.assertEqual(shape['allocationBytes'], 54976)
        source = ARCHIVES['candidate']['src/experimental_swift_reactor/cache_tests.rs'].decode()
        self.assertIn('assert_eq!(alloc.attempts,5); assert_eq!(alloc.reallocations,0);', source)
        REPORT['DeltaExisting'] = 0
        REPORT['operationBytes'] = {'baseline':92350, 'candidate':112822, 'delta':20472}

    def test_14_hit_work_allocator_and_all_eleven_absolute_snapshots(self):
        d = js(PRODUCER / 'hit-ledger-differential.json')
        left = [dict((k,int(v)) for k,v in re.findall(r'(\w+): (\d+)', r)) for r in records(B, 'COUNT_HIT_CHECKPOINT ')]
        right = [dict((k,int(v)) for k,v in re.findall(r'(\w+): (\d+)', r)) for r in records(C, 'COUNT_HIT_CHECKPOINT ')]
        self.assertEqual(len(left), 11); self.assertEqual(len(right), 11)
        for i, (old,new) in enumerate(zip(left,right)):
            self.assertEqual(d['checkpoints'][i]['baseline'],old); self.assertEqual(d['checkpoints'][i]['candidate'],new)
            self.assertEqual({k:v for k,v in old.items() if k not in ['construction','combined']},
                             {k:v for k,v in new.items() if k not in ['construction','combined']})
            self.assertEqual(new['construction']-old['construction'], 0 if i==0 else 20472)
            self.assertEqual(new['combined']-old['combined'], 0 if i==0 else 20472)
        for text in [B,C]:
            row=json_records(text,'COUNT_HIT ')[0]
            self.assertEqual((row['work256'],row['allocations'],row['allocationBytes']), (2048,0,0))
        REPORT['hit'] = {'hits':256,'work':2048,'allocations':0,'allocatedBytes':0,'checkpoints':11,
                         'workParity':True,'allocationParity':True,'byteParity':False,'admittedReservationDelta':20472}

    def test_15_admission_regression_boundaries_no_allocation(self):
        self.assertEqual(records(B,'COUNT_ADMISSION '), [f'COUNT_ADMISSION headroom={n} accepted=true ownOperationBytes=92350' for n in [92350,112821,112822]])
        self.assertEqual(records(C,'COUNT_ADMISSION '), [f'COUNT_ADMISSION headroom={n} accepted={str(n>=112822).lower()} ownOperationBytes=112822' for n in [92350,112821,112822]])
        self.assertIn('assert_eq!(a.attempts,0);', (PRODUCER/'swift-probes.rs').read_text())
        REPORT['admissionRegressions'] = {'headrooms':[92350,112821], 'candidateAcceptedBoundary':112822, 'probeAllocations':0}

    def test_16_actual_oracle_source_and_independent_finite_sequence(self):
        source = (PRODUCER/'swift-probes.rs').read_text()
        for fragment in ['for capacity in 0..=64', 'for i in 0..384', 'assert_eq!(*f,expected.0)',
                         'assert_eq!(*pins,0)', 'assert_eq!(*time==0,expected.1==0)', 'min_by_key(|j|(slots[*j].unwrap().1,*j))']:
            self.assertIn(fragment, source)
        oracle = 'COUNT_ORACLE capacities=65 transitions=24576 full_identity_collision_slots_and_order=true cleanup_zero=true'
        self.assertEqual(records(B, 'COUNT_ORACLE '), [oracle]); self.assertEqual(records(C,'COUNT_ORACLE '),[oracle])
        # Independent sequence enumeration, distinct from the actual Rust replay.
        summaries = {}
        for policy in [False,True]:
            transitions=hits=misses=collisions=0
            h=hashlib.sha256()
            for capacity in range(1,65):
                slots=[None]*capacity; plans=[None]*512; seed=17
                for i in range(384):
                    seed=(seed*1664525+1013904223)&0xffffffff
                    f=100+seed%70+(512 if i%3==0 else 0)
                    index=next((j for j,s in enumerate(slots) if s is not None and s[0]==f),None)
                    if index is None:
                        misses+=1; reused=plans[f&511]==f
                        collisions+=plans[f&511] is not None and not reused; plans[f&511]=f
                        index=next((j for j,s in enumerate(slots) if s is None),None)
                        if index is None: index=min(range(capacity),key=lambda j:(slots[j][1],j))
                        slots[index]=(f,0 if policy and not reused else i+1)
                    else:
                        hits+=1; slots[index]=(f,i+1)
                    self.assertEqual(len({s[0] for s in slots if s is not None}),sum(s is not None for s in slots))
                    h.update(canonical([capacity,i,f,index,slots])); transitions+=1
            self.assertEqual(transitions,24576)
            summaries['candidate' if policy else 'baseline']={'transitions':transitions,'hits':hits,'misses':misses,
                                                              'planCollisions':collisions,'stateStreamSHA256':h.hexdigest()}
        REPORT['finiteSequenceEnumeration'] = summaries
        REPORT['oracleScope'] = 'Producer actual Rust aggregate and assertion source audited; independent Python enumerates input/model states, not fresh VM execution'

    def test_17_every_work_and_cancellation_prefix_and_three_allocations(self):
        expected = {'baseline':[(129,74,95),(119,67,119)], 'candidate':[(186,76,111),(176,69,176)]}
        for side,text in [('baseline',B),('candidate',C)]:
            rows=records(text,'COUNT_PREFIX ')
            self.assertEqual(len(rows),2)
            for index,row in enumerate(rows):
                values=tuple(int(re.search(key+r'=(\d+)',row)[1]) for key in ['work','cancellation_checks','scanned_then_failed'])
                self.assertEqual(values,expected[side][index]); self.assertIn('allocation_failures=3 cleanup_zero=true',row)
                self.assertIn('eviction_prefixes={0}' if index==0 else 'eviction_prefixes={1, 2}',row)
        source=(PRODUCER/'swift-probes.rs').read_text()
        for fragment in ['for prefix in 0..work', 'for ordinal in 0..checks', 'for allocation in 0..3',
                         'plan_reuse_primary(e,r)', 'assert_eq!(s.injected_failures,1)', 'assert_eq!(c.usage(None).cache_work,stopped)']:
            self.assertIn(fragment,source)
        REPORT['failurePrefixes'] = expected

    def test_18_three_victim_prefixes_and_opaque_held_pin(self):
        for text,work in [(B,204),(C,261)]:
            self.assertEqual(records(text,'COUNT_MULTIVICTIM '),[f'COUNT_MULTIVICTIM shorter_work={work} actual_completed_prefixes={{0, 1, 2, 3}} held_pin_and_allocation_preserved=true cleanup_zero=true'])
        source=(PRODUCER/'swift-probes.rs').read_text()
        for fragment in ['assert_eq!(prefixes,[0,1,2,3].into_iter().collect())', 'assert_eq!(e.code,"all_entries_pinned")',
                         'instructions.as_ptr() as usize,ptr', 'cache.release(held', 'pi::key(&cache,35),Some(35)']:
            self.assertIn(fragment,source)
        REPORT['threeVictimEvictionPrefixes']=[0,1,2,3]

    def test_19_identity_collision_failed_scan_and_phase_regressions(self):
        for text in [B,C]:
            self.assertEqual(records(text,'COUNT_OWNERS '),['COUNT_OWNERS full_identity=4 original_collision=3 held_actual_pin_and_allocation=true failed_real_scan_no_plan=true cleanup_zero=true'])
        for text,expected in [(B,[64,64,64]),(C,[81,128,81])]:
            self.assertEqual([int(re.search(r'decodes=(\d+)',r)[1]) for r in records(text,'COUNT_PHASE ')],expected)
        self.assertIn('COUNT_COLLISION_PHASE decodes=64',B);self.assertIn('COUNT_COLLISION_PHASE decodes=128',C)
        REPORT['phaseDecodes']={'baseline':[64,64,64],'candidate':[81,128,81], 'collisionPhase':[64,128]}

    def test_20_source_failure_order_and_original_hit_tail(self):
        path='src/experimental/cache/borrowed.rs'
        old=ARCHIVES['baseline'][path].decode(); new=ARCHIVES['candidate'][path].decode()
        old=old[old.index('fn pin_acquired<M: CacheMode>'):]
        new=new[new.index('fn pin_acquired<M: CacheMode>'):]
        tail=old[old.index('    let slot = &mut parts.slots[index];'):old.rfind('\n}')]
        literal='\n'.join('    '+line for line in tail.splitlines())
        self.assertIn(literal,new[:new.index('    } else {')])
        self.assertLess(new.index('M::prepare_miss_publication(meter)'),new.index('M::resident_insert('))
        self.assertLess(new.index('M::resident_insert('),new.index('parts.slots[index].set(entry)'))
        self.assertIn('let _ = M::drop_entry(entry, meter);\n            let _ = meter.construction(0);\n            return Err(error);',new)
        source=ARCHIVES['candidate']['src/experimental_swift_reactor/cache.rs'].decode()
        scan=source[source.index('    fn scan(\n',source.index('impl CacheMode for SwiftMode')):]
        scan=scan[:scan.index('    fn build(')]
        self.assertEqual(scan.count('meter.work(41)?'),2)
        self.assertLess(scan.index('meter.work(41)?; // before outcome'),scan.index('scratch.plans[index] = Some(ScanPlan'))
        for fragment in ['plan.body_offset != body.body_offset', 'plan.body_len != body.body.len()', 'plan.type_index != body.type_index']:
            self.assertIn(fragment,scan)
        REPORT['sourceReasoning']={'literalHitTail':True,'preparationBeforeIndexMutation':True,
                                   'outcomeChargeBeforeColdPlanPublication':True,'fallibleFailuresDropAttemptedOwner':True,
                                   'scope':'Source order audit, not a proof of all Rust executions or release authorization'}

    def test_21_limits_dependencies_and_original_test_bytes_unchanged(self):
        for file in ['Cargo.toml','Cargo.lock','src/experimental_swift_reactor/control.rs']:
            self.assertEqual(ARCHIVES['baseline'][file],ARCHIVES['candidate'][file])
        common=(ROOT/'verification/swift-cost-retention-candidate/common-tests.rs').read_bytes()
        for mode in ['tested-baseline','candidate']:
            self.assertIn(common,ARCHIVES[mode]['src/experimental_swift_reactor/cache_tests.rs'])
        self.assertEqual(js(PRODUCER/'inputs.json')['limits'],{'cacheBytes':16777216,'cacheWork':64000000,'combinedBytes':268435456,
                                                            'entries':64,'entryBytes':8388608,'pins':64,'tickets':86})

    def test_22_frozen_model_and_review_packets_unchanged(self):
        for binding in js(PRODUCER/'inputs.json')['seals']:
            path=ROOT/binding['seal'];self.assertEqual(digest(path.read_bytes()),binding['sha256'])
            seal=js(path);self.assertEqual(len(seal['members']),binding['members'])
            for member in seal['members']:
                data=(ROOT/member['path']).read_bytes();self.assertEqual(digest(data),member['sha256'])
        REPORT['frozenPackets']=[{'seal':b['seal'],'sha256':b['sha256'],'members':b['members']} for b in js(PRODUCER/'inputs.json')['seals']]

    def test_23_cleanup_identity_absence_and_precise_scope(self):
        ownership=js(PRODUCER/'ownership.json'); preflight=js(PRODUCER/'cleanup-preflight.json'); cleanup=js(PRODUCER/'cleanup.json')
        self.assertEqual(ownership,preflight['ownership']);self.assertEqual(ownership,cleanup['ownership'])
        self.assertTrue(preflight['matchingIdentity']);self.assertTrue(preflight['synchronousChildrenOnly']);self.assertTrue(cleanup['removed'])
        self.assertEqual(pathlib.Path(ownership['path']),PRODUCER/'.scratch')
        self.assertFalse(pathlib.Path(ownership['path']).exists())
        receipt=js(PRODUCER/'receipt.json');self.assertTrue(receipt['allSynchronousChildrenCompleted'])
        self.assertEqual(receipt['fullTarget'],'not run');self.assertEqual(receipt['nativeUIAndCapture'],'not used; paused')
        REPORT['cleanup']={'ownedScratchAbsentNow':True,'producerOwnershipIdentityPreserved':True,
                           'processScope':'No fresh process discovery; historical synchronous completion receipts audited'}

if __name__ == '__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ResultAudit)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    REPORT.update({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'decision':'accept-recorded-rejection-only' if result.wasSuccessful() else 'audit-incomplete',
                   'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                   'nativeUIAndCapture':'not used; paused','fullTarget':'not run','freshRustReplay':'not run',
                   'noCandidateCorrectnessAcceptance':True})
    (OUT/'audit-results.json').write_bytes(canonical(REPORT))
    sys.exit(0 if result.wasSuccessful() else 1)
