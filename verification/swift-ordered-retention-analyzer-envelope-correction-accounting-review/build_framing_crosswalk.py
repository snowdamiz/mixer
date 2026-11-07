#!/usr/bin/env python3
"""Exact accepted-call crosswalk only; does not re-prove or replay framing22."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from admit_proposal import verify_proposal

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
INPUT = OWN/'commands/proposal-admission-1/inputs'
BASE = OWN/'commands/framing-baseline-admission-1'
def sha(data): return hashlib.sha256(data).hexdigest()
def main():
    old = (BASE/'analyzer.rs').read_bytes(); new_parent = (INPUT/'source-analyzer.rs').read_bytes(); new_leaf = (INPUT/'source-envelope.rs').read_bytes()
    assert new_parent.startswith(old)
    old_lines = old.decode().splitlines(); new_lines = new_leaf.decode().splitlines()
    def line(lines, text):
        matches = [i+1 for i,s in enumerate(lines) if s.strip() == text]
        assert len(matches) == 1, (text,matches)
        return matches[0]
    pairs = [
        ('ordinary loop', 'for index in 0..s.physical {', 'for index in 0..s.physical {', 'unchanged iteration extent; additional leaf work is outside inherited subdivision'),
        ('mandatory preflight', 'if budget.replay_left < RECORD_PREFLIGHT { s.limited = true; break; }', 'if budget.replay_left < RECORD_PREFLIGHT { s.limited = true; break; }', 'same8192 threshold, no lower B-specific threshold'),
        ('atomic main debit call', 'budget.replay(RECORD_STEPS)?;', 'budget.replay(COMBINED_RECORD)?; p.debit += RECORD_ENVELOPE;', 'same generic Budget.replay helper once; n value changes by explicit contract amendment only; added debit update is W01'),
        ('record backing and decoder', 'let mut w = [0;16]; reader.words(input, arena, budget, &mut w)?;', 'let mut w = [0; 16]; reader.words(input, arena, budget, &mut w)?;', 'same complete128 backing and one unchanged Reader.words call; no new private-leaf typed access inherits this work'),
        ('record offset', 'let offset = 512 + index * 128;', 'let offset = 512 + index * 128;', 'same arithmetic'),
        ('field/profile join', 'if !record_fields(arena, &w, f) { return Err(error(SCHEMA, RECORD_STAGE, offset, index + 1)); }', 'if !record_fields(arena, &w, f) { return Err(error(SCHEMA, RECORD_STAGE, offset, index + 1)); }', 'same helper/body and one call per decoded record'),
        ('wire coordinate', 'if !s.coordinate(&w) { return Err(error(COORDINATE, RECORD_STAGE, offset, index + 1)); }', 'if !s.coordinate(&w) { return Err(error(COORDINATE, RECORD_STAGE, offset, index + 1)); }', 'same Framing80 coordinate owner/helper and one call; new arena coordinates remain separate'),
    ]
    mapped = [{'role':role,'accepted_line':line(old_lines,a),'proposal_line':line(new_lines,b),'accepted_statement':a,'proposal_statement':b,'assessment':note} for role,a,b,note in pairs]
    verify_proposal()
    result = {'schema':1,'at':datetime.now(timezone.utc).isoformat(),
              'status':'inherited22-call-shape-crosswalk-supported-no-baseline-reproving',
              'accepted_source_sha256':sha(old),'proposal_parent_sha256':sha(new_parent),'proposal_envelope_sha256':sha(new_leaf),
              'accepted_step_declaration':{'path':'docs/swift-ordered-retention-analyzer-library.md','sha256':sha((BASE/'swift-ordered-retention-analyzer-library.md').read_bytes()),'lines':[116,124],'framing_debit':22},
              'accepted_source_exact_prefix':True,'crosswalk':mapped,
              'unchanged_called_definitions_by_exact_prefix':['Budget.replay','Reader.words','Reader.take','record_fields','full_identity','Framing.coordinate','error'],
              'separately_charged_added_work':{'private_word_reads_shape_coordinates_transition_staging_commit_replies':'L01-L14 and linked helpers','new debit/record/progress/StepBudget/poison handling':'W01-W09','candidate/setup calls/initializer':'S01-S06','progress initialization and new argument chain':'T01-T03','finalize/project helpers':'E01-E10; C1 funding gap remains','aggregate/changed error results':'F01-F04'},
              'limitations':['Reuses the previously accepted22 source boundary; does not independently requalify that historical bound','Changed n argument requires root-selected numeric contract; no current B471 execution qualification','C1 early-error funding and C2 complete Result sizes remain unresolved'],
              'baseline_or_cost_dependent_replay':False,'numeric_selection':False}
    (OWN/'framing22-crosswalk.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':result['status'],'mapped_record_operations':len(mapped),'numeric_selection':False},sort_keys=True))
if __name__ == '__main__':main()
