"""Explicit conservative named-role inventory, not a stack/RSS measurement."""
import json
from pathlib import Path

RESERVATIONS = {'wire': 3072, 'candidate': 2048, 'io': 4096, 'metadata': 4096,
                'setup': 12288, 'control': 8192, 'report': 8192}
# Each helper lease includes ALL argument values/borrows, scalar locals,
# checked Option intermediates, complete fixed error/Result return place AND
# caller receiving place. Large named objects have disjoint groups below.
HELPERS = {
 'api': (288, 'four File borrows32; returned/receiving Outcome Results2x104; nested-call argument copies40; padding8'),
 'core': (1280, 'args40; Budget56; Framing80; error32; Decision8; bool1; Result<bool,Error>40; matched error32; Outcome104; complete Outcome return/receiving/move places4x104; complete setup/write/budget Results4x40; scalar/borrow/branch temporaries311'),
 'error': (128, 'code/stage/offset/record args24; produced/returned/receiving Error3x32; padding8'),
 'getters': (96, 'three self borrows3x8; three returned/receiving bool pairs6; comparison/scalar/padding66'),
 'arena_new': (192, 'budget/fn/call borrows24; complete Arena Results3x40; error32; padding16'),
 'arena_new_with': (256, 'args16; region/end/next/indices/borrow temporaries64; three complete checked-call Results3x40; checked Option16; error32; padding8'),
 'range': (384, 'Region/index/field/width args48; error32; eight checked Option<usize> slots128; start/end/region_end24; Range16; complete Range Results2x40; padding56'),
 'get64': (256, 'args48; Range Result40; Range16; slice Option16; borrowed bytes16; copied eight bytes8; complete value Results2x40; error32'),
 'get32': (256, 'same checked get64 lease, complete four-byte temporary rounded to8'),
 'put64': (288, 'args56; Range Result40; Range16; slice Option16; bytes borrow16; LE temporary8; complete unit Results2x40; error32; padding24'),
 'put32': (288, 'same put64 lease; complete four-byte LE temporary rounded to8'),
 'budget_new': (256, 'limit8; produced Budget56; complete Budget Results2x64; checked Option16; error32; padding16'),
 'budget_replay': (192, 'self/n args16; checked Option16; scalar operands24; error32; complete unit Results2x40; padding24'),
 'budget_setup': (192, 'self/n args16; checked Option16; scalar operands24; error32; complete unit Results2x40; padding24'),
 'budget_io': (192, 'self8; scalars/branches/borrow40; error32; complete unit Results2x40; padding32'),
 'budget_report': (192, 'same complete roles as budget_setup'),
 'budget_used': (32, 'self8; returned/receiving u64 pair16; scalar8'),
 'stamp_len': (96, 'complete by-value Stamp72; returned/receiving u64 pair16; padding8'),
 'context': (512, 'args24; row/copy/check indices48; complete Fixture return/receiving Results2x80; produced Fixture72; four complete helper Results4x40; error32; padding16'),
 'profile': (768, 'args96; row/defined/type20; checked Option16; eight complete helper Results8x40; complete unit return/receiving Results2x40; error32; scalar/borrow/padding204'),
 'header': (384, 'args96; tuple/index/iteration scalar48; two nested Results2x40; returned/receiving unit Results2x40; error32; padding48'),
 'identity': (256, 'Fixture/ref/release args96; function/row16; three complete identity-value Results3x40; boolean return/receiving/comparison/padding24'),
 'record_fields': (192, 'Fixture/arena/wire args88; all named and expression bool/scalar temporaries64; returned/receiving bool pair2; padding38'),
 'framing_new': (192, 'physical8; produced/returned Framing160; scalar/padding24'),
 'coordinate': (128, 'self/wire refs16; checked Option16; scalar/comparison/boolean/borrow temporaries94; returned/receiving bool pair2'),
 'footer': (384, 'args40; fail32; checked Options32; complete helper and return Results4x40; scalar/borrow/branch/padding120'),
 'walk': (512, 'args112; index/offset/target/available/count/copy locals56; loop iterator16; four complete helper Results4x40; returned/receiving unit Results2x40; error32; padding56'),
 'initial': (256, 'args16; returned/receiving Result<Stamp,Error>2x80; position8; error32; complete budget-call Result40'),
 'stable': (256, 'input/Stamp/budget args88; complete returned/receiving unit Results2x40; error32; helper Result40; scalar/padding16'),
 'output_safety': (384, 'five borrows40; pos/indices24; two loop iterators32; returned/receiving Stamp Results2x80; helper Result40; error32; scalar/borrow/padding56'),
 'observe': (512, 'six refs48; Fixture72; complete return/receiving Results2x40; six setup/profile/walk/stability Result slots6x40; error32; scalar/borrow/padding40'),
 'write_report': (768, 'output/Stamp/arena/budget/Outcome/Framing args184; scalar indices/value/position/done/count40; iterators56; six complete helper Results6x40; returned/receiving Results2x40; error32; padding136'),
 'file_wrappers': (128, 'one live File stamp wrapper borrow8 and complete IO Result80, or position borrow8/Result16; nested return moves additionally charged metadata; padding40'),
}
PHASES = {
 'setup_budget': ['api','core','budget_new','error'],
 'output_no_alias_metadata': ['api','core','output_safety','file_wrappers','error'],
 'arena_reserve': ['api','core','arena_new','arena_new_with','error'],
 'arena_initialize': ['api','core','arena_new','arena_new_with','budget_replay','error'],
 'arena_sentinels': ['api','core','arena_new','arena_new_with','put64','range','budget_setup','budget_replay','error'],
 'initial_input_metadata': ['api','core','observe','initial','file_wrappers','error'],
 'context_block_read': ['api','core','observe','context','budget_io','error'],
 'context_checked_copy': ['api','core','observe','context','put64','range','budget_setup','budget_replay','error'],
 'context_checked_validate': ['api','core','observe','context','get64','range','error'],
 'profile_block_read': ['api','core','observe','profile','budget_io','error'],
 'profile_checked_publish': ['api','core','observe','profile','put64','range','budget_replay','error'],
 'header_join': ['api','core','observe','walk','header','get64','range','error'],
 'record_fields_identity': ['api','core','observe','walk','record_fields','identity','get64','range','error'],
 'record_coordinate': ['api','core','observe','walk','coordinate','error'],
 'limited_drain': ['api','core','observe','walk','budget_setup','budget_replay','budget_io','error'],
 'footer_decode_check': ['api','core','observe','walk','footer','budget_setup','budget_replay','error'],
 'input_final_metadata': ['api','core','observe','stable','file_wrappers','error'],
 'report_zero_encode': ['api','core','write_report','put64','range','budget_report','error'],
 'report_digest_echo': ['api','core','write_report','get64','put64','range','budget_report','error'],
 'report_write_metadata': ['api','core','write_report','file_wrappers','error'],
 'return_or_error': ['api','core','getters','budget_used','error'],
}
# Deliberate distinct-role union within each group, including moves which can
# never be simultaneous. This conservative bound avoids claiming exact peaks.
ROLES = {
 'wire': [
  ('walk header/footer/record arrays',512+512+128),('profile header/row arrays',512+32),
  ('context decoded header/single-word array',128+8),('Reader.words raw512/eight-byte copy/iterator/word slice',512+8+24+16)],
 'candidate': [],
 'io': [
  ('bounded_read complete args/locals/read-Result/error/return/caller/read-call borrows',256),
  ('eof complete args/byte/iteration/read-Result/error/return/caller/read-call borrows',256),
  ('Reader.take complete args/loop/cursors/slices/helper-Result/error/return/caller',256),
  ('Reader.words arguments/helper-Result/return/caller/slice temporaries excluding wire buffers',192),
  ('Reader.new produced/returned/receiving Reader plus args',112),('three caller Reader owners',3*48),
  ('output bytes slice/write-Result/error/offset/iteration/error-return places',256)],
 'metadata': [
  ('all four caller File owners retained through borrows',16),('file_stamp File borrow',8),
  ('complete File.metadata Result and extracted Metadata',152+144),
  ('constructed Stamp and IO return/wrapper/caller moves',72+3*80),
  ('initial Stamp and complete IO Results/position Result',72+80+16),
  ('observe_inputs three initial Stamp owners',3*72),('stable before Stamp and IO result',72+80),
  ('output_safety a,b,c,d and complete all array',4*72+4*72),
  ('output_safety returned/receiving Stamp and core retained output_initial',2*72+72),
  ('write_report by-value initial/before/after Stamps and complete IO results',3*72+2*80),
  ('four position-wrapper complete IO Results',4*16)],
 'setup': [
  ('Arena/Vec local/produced/core owner moves',3*24),('complete Arena return/wrapper/caller Results',3*40),
  ('reserve complete Result/error/caller slots',3*16),('reserve function pointer argument',8),
  ('zero initializer8; REGIONS literal288; complete IntoIter bounded336; region/end/next/loop scalars',8+288+336+128),
  ('five small-row/init Range iterators',5*16),
  ('all context numeric comparison literals',40),('profile expected/reserved/tuple literal and complete tuple iterator',368),
  ('header expected/reserved/tuple literals and complete tuple iterator',528),
  ('record absent/zero literals for every source occurrence',128),('coordinate kind literal',24),('footer reserved literal',160)],
 'report': [
  ('write_report complete fixed header',256),('header enumerate/value and zero/report loops',128),
  ('core outcome plus public/core/caller return receiving and branch move places',5*104),
  ('Outcome error/decision/matched error and complete Result<bool,Error> moves',32+8+32+2*40),
  ('complete report helper/error/caller Results and Error copies',6*40+4*32),
  ('final steps/position/counter/borrow/enum temporaries',256)],
}

def build():
    used={group:sum(n for _,n in rows) for group,rows in ROLES.items()}
    phases={name:sum(HELPERS[helper][0] for helper in chain) for name,chain in PHASES.items()}
    used['control']=max(phases.values())
    for group,n in used.items(): assert n<=RESERVATIONS[group], (group,n)
    assert sum(RESERVATIONS.values())==41984
    assert sum(RESERVATIONS.values())<=65536
    return {'schema':1,'kind':'conservative-complete-named-role-inventory-for-fixture-foundation',
      'reservations':RESERVATIONS,'named_role_upper_by_group':used,'named_role_upper_total':sum(used.values()),
      'reserved_total':sum(RESERVATIONS.values()),'unassigned_margin':65536-sum(RESERVATIONS.values()),
      'helper_leases':{k:{'bytes':n,'roles':roles} for k,(n,roles) in HELPERS.items()},
      'phases':{k:{'control_upper':phases[k],'call_chain':chain} for k,chain in PHASES.items()},
      'roles':{k:[{'roles':name,'bytes':n} for name,n in rows] for k,rows in ROLES.items()},
      'arena_backing_bytes':8388608,'allocation_count':1,'safe_file_owners_created_inside_library':0,
      'excluded':'stdlib/allocator/kernel internals, optimizer copies, physical stack/TLS/RSS, test harness and caller paths; no physical-memory qualification',
      'limitations':'Authored conservative logical inventory requiring independent source review; no semantic candidate/CLI/host custody/preparer/native/target authority'}

if __name__=='__main__':
    print(json.dumps(build(),sort_keys=True,indent=2))
