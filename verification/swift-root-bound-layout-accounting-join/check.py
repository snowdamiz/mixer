#!/usr/bin/env python3
"""Read-only source-join integrity and finite negative controls; no lane replay."""
from pathlib import Path
import copy
import json
import time
import build

D=Path(__file__).resolve().parent

def data():
    return {'catalogue':build.decode((D/'layout-crosswalk.json').read_bytes())['catalogue'],
        'place_join':build.decode((D/'inventory-place-join.json').read_bytes()),
        'obligations':build.decode((D/'obligation-dispositions.json').read_bytes())['obligations'],
        'differences':build.decode((D/'representation-differences.json').read_bytes())['differences']}
def expected():
    inventory=build.decode((build.I/'delta-inventory.json').read_bytes());accepted=build.decode(build.A.read_bytes())['acceptance'];query=build.decode((build.V3/'plan.json').read_bytes())
    return build.make(inventory,accepted,query)
def validate(current,oracle):
    build.need(current==oracle,'finite join differs from pinned input reconstruction')
    build.need(current['place_join']['counts']=={'arguments':65,'locals_returns':580,'total_roles':645,'named_shape_roles':97,'actual_closure_roles':2,'unbound_roles':546},'finite role counts')
    build.need(len(current['catalogue'])==29 and len(current['obligations'])==24,'complete shape/obligation frontier')
    for item in current['obligations']:
        build.need(item['status']=='OPEN_FOR_INCREMENTAL_ACCOUNTING' and item['numeric_storage_charge_proposed_closed'] is False,'invented accounting closure')
        build.need(item['work_price'] is None and item['storage_charge_bytes'] is None,'invented price')
    for role in current['place_join']['roles']:
        build.need(role['physical_storage_region_id'] is role['lifetime_interval'] is role['incremental_charge_bytes'] is role['runtime_work_price'] is None,'invented live region/price')
    values={r['id']:r['difference_bytes'] for r in current['differences']}
    build.need(values=={'D01':8,'D02':8,'D03':8,'D04':8,'D05':16,'D06':16,'D07':32,'D08':0,'D09':0,'D10':0,'D11':0,'D12':0,'D13':0,'D14':0},'exact representation arithmetic')

def main():
    start=time.monotonic();manifest=build.decode((D/'input-manifest.json').read_bytes())
    for row in manifest['inputs']:
        build.need(time.monotonic()-start<30,'finite check deadline');build.pin(row)
    build.pin(manifest['python']['tool'])
    current=data();oracle=expected();validate(current,oracle);controls=[]
    def reject(name,mutate):
        altered=copy.deepcopy(current);mutate(altered)
        try:validate(altered,oracle)
        except ValueError as error:controls.append({'name':name,'rejected':True,'reason':str(error)})
        else:raise AssertionError('accepted adverse accounting join:'+name)
    reject('changed-observed-layout-size',lambda d:d['catalogue'][22].update(size=13616))
    reject('changed-observed-closure-align',lambda d:d['catalogue'][28].update(align=16))
    reject('missing-frontier-shape',lambda d:d['catalogue'].pop())
    reject('duplicate-frontier-shape',lambda d:d['catalogue'].append(copy.deepcopy(d['catalogue'][0])))
    reject('missing-storage-obligation',lambda d:d['obligations'].pop())
    reject('invented-closed-storage-charge',lambda d:d['obligations'][12].update(numeric_storage_charge_proposed_closed=True))
    reject('zero-work-price-from-layout',lambda d:d['obligations'][0].update(work_price=0))
    reject('zero-storage-price-from-same-size-option',lambda d:d['catalogue'][26].update(numeric_charge_bytes=0))
    reject('invented-positive-storage-grant',lambda d:d['obligations'][16].update(storage_charge_bytes=13640))
    reject('missing-inventory-place',lambda d:d['place_join']['roles'].pop())
    reject('summed-645-places-as-peak',lambda d:d['place_join'].update(peak_storage_bytes=999999))
    def borrowed_as_value(d):
        role=next(r for r in d['place_join']['roles'] if r['type_spelling']=="&PrepaidCorrelationAttemptV1<'_, '_>")
        role['layout_id']='L02'
    reject('borrowed-attempt-not32-byte-value',borrowed_as_value)
    def generic_as_file(d):
        role=next(r for r in d['place_join']['roles'] if 'LoaderCarrierCoreV1<R>' in r['type_spelling'])
        role['layout_id']='L05'
    reject('generic-R-not-File-instantiation',generic_as_file)
    def other_closure(d):
        role=next(r for r in d['place_join']['roles'] if ':1187:22: 1187:38}' in r['type_spelling'])
        role['layout_id']='L29'
    reject('other-identity-closure-not-dispatch48',other_closure)
    reject('semantic-move-invents-physical-alias',lambda d:d['place_join']['roles'][0].update(physical_storage_region_id='assumed-same-slot'))
    reject('invented-live-interval',lambda d:d['place_join']['roles'][0].update(lifetime_interval=[0,1]))
    reject('nested-aggregate-double-charge',lambda d:d['catalogue'][24].update(numeric_charge_bytes=13640+13624))
    reject('child-token-refunds-acquisition',lambda d:d['obligations'][-1].update(acquisition_refund_authorized=True))
    reject('wrong-wrapper-uplift-arithmetic',lambda d:d['differences'][0].update(difference_bytes=16))
    reject('zero-difference-becomes-zero-work',lambda d:d['differences'][7].update(work_price=0))
    reject('duplicate-relocated-leaf-charge',lambda d:next(r for r in d['obligations'] if r['id']=='W04').update(dynamic_leaf_invocations=2))
    prospective=build.decode((D/'prospective-controls.json').read_bytes());next_contract=build.decode((D/'next-contract.json').read_bytes())
    build.need(len(prospective['controls'])==16 and next_contract['select_storage_grant'] is next_contract['select_work_prices'] is False,'proposal only scope')
    report={'schema':1,'status':'SOURCE_JOIN_INTEGRITY_AND_NEGATIVE_CONTROLS_PASSED','controls':controls,'controls_passed':len(controls),
        'place_binding_coverage':current['place_join']['counts'],'all24_accounting_obligations_remain_open':True,
        'numeric_storage_charge_obligations_closed':0,'elapsed_seconds':time.monotonic()-start,
        'compiler_parser_runtime_child_replays':0,'scope':'Finite evidence/data integrity controls only; prospective lifetime/backing/runtime accounting controls not executed.'}
    print(json.dumps({'status':report['status'],'controls':len(controls),**current['place_join']['counts'],'storage_charge_obligations_closed':0,'elapsed_seconds':report['elapsed_seconds']}))
    return report
if __name__=='__main__':main()
