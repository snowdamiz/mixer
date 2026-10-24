#!/usr/bin/env python3
"""Frozen-input observations for catalog uniqueness before ignored-name discard."""
import argparse,copy,gzip,hashlib,json,pathlib,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
ATTEMPT=HERE
sys.path.insert(0,str(ATTEMPT/'candidate'))
from inspector import decode,validate,canonical
from raw_validation import validate_raw

def execute():
    p=ATTEMPT/'inputs/inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz'
    original=decode(gzip.decompress(p.read_bytes()))['raw'];expected=decode((ATTEMPT/'inputs/selected-expected.json').read_bytes())
    observations=[]
    for mode in ['internal/internal same relation','internal/external same relation','same name different relations portable']:
        selected=None
        for i,a in enumerate(original['enforcement']['triggers']):
            if not a['internal']:continue
            for j,b in enumerate(original['enforcement']['triggers']):
                same=a['relation_oid']==b['relation_oid']
                if i!=j and ((mode=='internal/internal same relation' and same and b['internal']) or
                             (mode=='internal/external same relation' and same and not b['internal']) or
                             (mode=='same name different relations portable' and not same)):
                    selected=(i,j);break
            if selected:break
        assert selected,mode
        x=copy.deepcopy(original);a=x['enforcement']['triggers'][selected[0]];b=x['enforcement']['triggers'][selected[1]];old=a['name'];a['name']=b['name']
        before=canonical(x)
        def outcome(fn):
            try:fn();return True,None
            except ValueError as exc:return False,str(exc)
        raw_admitted,raw_error=outcome(lambda:validate_raw(x));selected_admitted,selected_error=outcome(lambda:validate(x,expected))
        expected_admitted=a['relation_oid']!=b['relation_oid']
        assert raw_admitted==selected_admitted==expected_admitted
        assert canonical(x)==before
        observations.append({'mode':mode,'mutated_oid':a['oid'],'peer_oid':b['oid'],'relation_oid':a['relation_oid'],'peer_relation_oid':b['relation_oid'],'relation':a['relation'],'old_name':old,'new_name':a['name'],'raw_admitted':raw_admitted,'selected_admitted':selected_admitted,'raw_error':raw_error,'selected_error':selected_error,'expected_admitted':expected_admitted,'input_unchanged':True,'violates_retained_pg_trigger_unique_key':a['relation_oid']==b['relation_oid'],'finding_observation_not_security_pass':a['relation_oid']==b['relation_oid']})
    h=ATTEMPT/'inputs/platform-catalog-types/catalog/pg_trigger.h';line='DECLARE_UNIQUE_INDEX(pg_trigger_tgrelid_tgname_index, 2701, TriggerRelidNameIndexId, pg_trigger, btree(tgrelid oid_ops, tgname name_ops));';assert line in h.read_text()
    return {'schema':1,'finding':'ACSR02','scope':'frozen review model replay; two required malformed rejections and one selected portability admission; no ordinary-runtime bypass','source_digest':'3760cbfe5bb28407ce58d678eef22b064a960126d659df031cf11007b789d6d8','input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'header_sha256':hashlib.sha256(h.read_bytes()).hexdigest(),'header_unique_index':line,'observations':observations,'historical_malformed_now_rejected':2,'valid_portability_control':1}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();result=execute();pathlib.Path(args.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
