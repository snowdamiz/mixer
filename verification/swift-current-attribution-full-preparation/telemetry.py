"""Separate, non-authoritative telemetry classification; never a guest oracle."""
import json
LABELS = ('constructed','initialize','corpus_1','corpus_2','before_cleanup','final_cleanup')
ENVELOPE = 4608
LIFETIME = 27648

def classify(path, original):
    issues=[];rows=[];total=0
    expected=[e['event'] for e in original if e['event'] in LABELS[:-1]]
    if any(e['event']=='final_cleanup_usage' for e in original):expected.append('final_cleanup')
    try:
        for line in path.read_bytes().splitlines(keepends=True):
            at=line.find(b'MIXER_ATTRIBUTION ')
            if at<0:continue
            encoded=line[at:];total+=len(encoded)
            if len(encoded)>ENVELOPE:issues.append('envelope_overflow')
            def pairs(items):
                value={}
                for k,v in items:
                    if k in value:raise ValueError('duplicate key')
                    value[k]=v
                return value
            try:rows.append(json.loads(encoded[len(b'MIXER_ATTRIBUTION '):],object_pairs_hook=pairs))
            except (ValueError,TypeError,UnicodeError):issues.append('malformed_telemetry')
        if len(rows)>6 or total>LIFETIME:issues.append('lifetime_output_overflow')
        labels=[r.get('lifecycle') for r in rows]
        if labels!=expected:issues.append('missing_duplicate_or_out_of_order_lifecycle')
        for i,row in enumerate(rows,1):
            if row.get('lifecycle') not in LABELS:issues.append('unknown_lifecycle')
            if row.get('sequence')!=i or row.get('reset_count')!=1:issues.append('sequence_or_reset_invalid')
            if row.get('prior_write_failed') is not False:issues.append('prior_write_failed')
            if row.get('formatted') is not True:issues.append('formatter_failed')
            if row.get('observer_invalid')!=0 or row.get('invariant_mask')!=0 or row.get('adapter_invalid')!=0 or row.get('valid') is not True:issues.append('invalid_telemetry')
            payload=row.get('payload')
            if row.get('formatted') is not True or row.get('observer_invalid')!=0 or row.get('invariant_mask')!=0 or row.get('adapter_invalid')!=0:
                if payload is not None:issues.append('invalid_payload_not_discarded')
                continue
            if not isinstance(payload,dict):issues.append('missing_payload');continue
            event=next((e for e in original if e['event']==row.get('lifecycle')),None)
            if row.get('lifecycle')=='final_cleanup':
                finals=[e['payload'] for e in original if e['event']=='final_cleanup_usage']
                pre=next((e['payload'] for e in original if e['event']=='before_cleanup'),None)
                if not finals or not isinstance(finals[-1],dict):issues.append('missing_original_final_usage')
                elif row.get('cache_work')!=finals[-1]['cache_work']:issues.append('final_original_work_mismatch')
                if row.get('decodes_bound_before_consumption') is not True:issues.append('missing_preconsumption_binding')
                if pre is not None and row.get('cache_decodes')!=pre['cache']['decodes']:issues.append('preconsumption_decode_mismatch')
                if pre is None and row.get('cache_decodes')!=0:issues.append('construction_decode_mismatch')
            elif event is not None:
                if row.get('cache_work')!=event['payload']['usage']['cache_work'] or row.get('cache_decodes')!=event['payload']['cache']['decodes']:issues.append('original_snapshot_mismatch')
            try:
                if payload['invalid']!=0 or sum(payload['credits'])!=row['cache_work']:issues.append('credit_sum_mismatch')
                if payload['completed']!=row['cache_decodes'] or payload['distinct']+payload['repeated']!=payload['completed']:issues.append('completion_mismatch')
                if sum(payload['scan_credits'])!=payload['credits'][6] or sum(payload['scan_calls'])!=payload['calls'][6] or sum(payload['scan_published'])!=payload['plans'][3]:issues.append('scan_partition_mismatch')
                if sum(payload['build_credits'])!=payload['credits'][13] or sum(payload['build_calls'])!=payload['calls'][13]:issues.append('build_partition_mismatch')
            except (KeyError,TypeError,ValueError,IndexError):issues.append('malformed_aggregate_fields')
    except Exception as error:
        issues.append('telemetry_parser_error:'+type(error).__name__)
    issues=list(dict.fromkeys(issues))
    return {'schema':1,'authority':'diagnostic telemetry only; original result and cleanup events authoritative','status':'valid' if not issues and rows else ('not_started' if not issues else 'invalid_or_missing'),'issues':issues,'expectedLabels':expected,'snapshots':rows,'outputBytes':total,'maximumBytes':LIFETIME,'originalResultReplaced':False,'cleanupTruthInferredFromTelemetry':False}
