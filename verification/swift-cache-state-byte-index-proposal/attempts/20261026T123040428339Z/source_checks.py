"""Finite source-only proposal construction/checks. Never executes Rust."""
from pathlib import Path
import datetime, difflib, hashlib, json, random, sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
C3 = REPO / "verification/swift-cache-state-implementation/correction-3"

def digest(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
def e(prefix, names): return [prefix + "." + x for x in names.split()]
def index(prefix): return e(prefix, "pointer length bounds normal_branch scale address")
def fields(prefix, names): return e(prefix, names)

# Actual source/received call edges, one event per representation component.
def call(name, args, body, returns=0):
    return (e(name, " ".join("arg_"+str(i) for i in range(args)))
            + e(name, " ".join("param_"+str(i) for i in range(args)))
            + [name+".call"] + body
            + e(name, " ".join("return_"+str(i) for i in range(returns)))
            + e(name, " ".join("received_"+str(i) for i in range(returns)))
            + e(name, "return_control caller_complete"))

def length(name): return call(name, 2, [name+".metadata_length"], 1)
def pointer(name): return call(name, 2, [name+".data_pointer"], 1)
def ub(name, predicate, nargs=2):
    # Enabled successful check is the conservative path. No panic body occurs.
    return call(name+".enabled",0,[name+".enabled_intrinsic"],1) + [name+".enabled_branch"] + call(name+".check", nargs, e(name, predicate)+e(name,"predicate_negation failure_branch"), 0)

def raw_parts(name):
    # Standard intrinsic boundary: successful raw pointer -> slice construction.
    aligned = call(name+".is_aligned_to",2,e(name,"pointer_to_integer alignment_minus_one alignment_mask alignment_zero"),1)
    aligned = call(name+".maybe_is_aligned",2,call(name+".const_eval_select",2,e(name,"runtime_selector runtime_branch")+aligned,1),1)
    nonnull = call(name+".is_null",1,[name+".null_compare"],1)
    aligned = call(name+".aligned_and_nonnull",3,aligned+e(name,"aligned_and is_zst_or")+nonnull+[name+".nonnull_not"],1)
    alloc = call(name+".is_valid_allocation_size",2,e(name,"size_zero size_branch max_to_usize max_div_size max_binding len_le_max"),1)
    body = e(name,"check_pointer_cast check_size_of check_align_of")
    condition = aligned+[name+".allocation_short_circuit"]+alloc+e(name,"predicate_negation failure_branch")
    body += call(name+".enabled",0,[name+".enabled_intrinsic"],1)+[name+".enabled_branch"]
    body += call(name+".precondition",4,condition,0)
    body += call(name+".slice_from_raw_parts", 2, e(name, "metadata_pointer metadata_length"), 2)
    body += e(name, "dereference_to_reference_pointer dereference_to_reference_length")
    return call(name, 2, body, 2)

def pointer_add(name):
    return call(name, 2, ub(name+".precondition", "size_product address_bound success_branch")
                + e(name, "scaled_offset address_sum"), 1)

def split_unchecked(name):
    body = length(name+".len") + [name+".len_binding"]
    body += pointer(name+".ptr") + [name+".ptr_binding"]
    body += ub(name+".mid_check", "mid_le_len success_branch")
    body += raw_parts(name+".left")
    body += pointer_add(name+".right_ptr")
    body += call(name+".unchecked_sub", 2, [name+".subtract"], 1)
    body += raw_parts(name+".right")
    body += e(name, "tuple_left_pointer tuple_left_length tuple_right_pointer tuple_right_length")
    return call(name, 3, body, 4)

def split_checked(name):
    body = length(name+".len") + e(name, "mid_le_len success_branch")
    body += split_unchecked(name+".unchecked")
    body += e(name, "Some_tag Some_left_pointer Some_left_length Some_right_pointer Some_right_length")
    return call(name, 3, body, 5)

def split(name):
    body = split_checked(name+".checked") + e(name, "Option_tag_read Some_branch pair_left_pointer pair_left_length pair_right_pointer pair_right_length")
    return call(name, 3, body, 4)

def as_chunks_unchecked(name):
    body = length(name+".check_len")
    condition = e(name,"N_nonzero N_short_circuit") + call(name+".is_multiple_of",2,e(name,"divisor_nonzero divisor_branch remainder remainder_zero"),1)
    body += call(name+".enabled",0,[name+".enabled_intrinsic"],1)+[name+".enabled_branch"]
    body += call(name+".N_check",2,condition+e(name,"predicate_negation failure_branch"),0)
    body += length(name+".len")
    body += call(name+".exact_div", 2, [name+".divide"], 1) + [name+".new_len_binding"]
    body += pointer(name+".as_ptr") + [name+".pointer_cast"]
    body += raw_parts(name+".raw_parts")
    return call(name, 2, body, 2)

def chunks(name):
    body = e(name, "N_nonzero assertion_branch") + length(name+".len")
    body += e(name, "len_div_N len_binding rounded_length")
    body += split(name+".split")
    body += e(name, "multiple_pointer_binding multiple_length_binding remainder_pointer_binding remainder_length_binding")
    body += as_chunks_unchecked(name+".chunks_unchecked")
    body += e(name, "array_pointer_binding array_length_binding tuple_array_pointer tuple_array_length tuple_remainder_pointer tuple_remainder_length")
    # Actual returned tuple and caller destructuring, not just live view fields.
    return call(name, 2, body, 4) + e(name, "caller_array_pointer_binding caller_array_length_binding remainder_pointer_discard remainder_length_discard")

def view(name, split_candidate=False, merge_call=False):
    result = e(name, "source_reborrow_pointer source_reborrow_length")
    if split_candidate:
        if merge_call: result += e(name,"merge_arg_thin merge_param_thin merge_call")
        result += e(name,"array_unsize_pointer array_unsize_length")
        result += split(name+".candidate_split")
        result += e(name, "time_bytes_pointer_binding time_bytes_length_binding indices_pointer_binding indices_length_binding shared_reborrow_pointer shared_reborrow_length")
    result += chunks(name+".as_chunks")
    if merge_call:
        result += e(name, "merge_unit_return merge_unit_received")
    return result

def word_load(name, cast=False):
    return (e(name, "row_scale base_add field_add")
            + ([name+".cast"] if cast else []) + index(name)
            + e(name, "LE scalar_return binding"))

def checked_arithmetic(name, operation):
    if operation=="add":
        body = call(name+".add_with_overflow",2,[name+".sum_and_overflow_intrinsic"],2)
        body += [name+".tuple_overflow_field"]
        body += call(name+".unlikely",1,[name+".branch_hint_identity"],1)
    else:
        body = [name+".self_lt_rhs"]
    body += [name+".normal_branch"]
    body += call(name+".unchecked_"+operation,2,[name+".arithmetic_intrinsic"],1)
    body += e(name,"Some_tag Some_payload")
    return call(name+".checked_"+operation,2,body,2)+e(name,"match_tag Some_branch payload_binding")

def store_word(name):
    # Expand the unchanged st helper and its safe range/copy platform closure.
    body = e(name, "end_add range_start_field range_end_field")
    body += call(name+".range_index_mut", 4,
        e(name, "range_start_read range_end_read start_le_end range_branch end_le_length bounds_branch pointer_read length_read range_address range_length")
        + e(name, "view_pointer view_length"), 2)
    body += call(name+".to_le_bytes", 1, [name+".LE"], 0)
    body += e(name, "array_return_control array_received_control source_borrow_pointer source_borrow_length")
    cp = e(name, "dest_length source_length lengths_equal length_branch")
    cp += ub(name+".copy_precondition", "destination_alignment source_alignment count_size nonoverlap success_branch")
    cp += e(name, "copy_destination_pointer copy_source_pointer copy_count copy_received_destination copy_received_source copy_received_count")
    body += call(name+".copy_from_slice", 4, cp, 0)
    return call(name, 4, body, 0)

def add_row(rows, owner, name, operations, multiplicity=1, copies=0, note=""):
    assert len(operations) == len(set(operations)), name
    rows.append(dict(owner=owner, site=name, scalar_events=operations,
        scalar_per_instance=len(operations), multiplicity=multiplicity,
        scalar_total=len(operations)*multiplicity, copies_per_instance=copies,
        copy_groups=copies*multiplicity, copy_bytes_each=8 if copies else 0, note=note))

def build_ledger():
    rows=[]
    # G2 complete changed probe region, including its final coherence checks.
    add_row(rows,"G2","probe_view",view("probe_view"))
    add_row(rows,"G2","probe_candidate_view",view("probe_candidate_view",True))
    add_row(rows,"G2","probe_initial",e("probe_initial", "resident_base_div resident_base_bind pin_base_div pin_base_bind resident_limit_field resident_limit_cast resident_limit_bind pin_limit_field pin_limit_cast pin_limit_bind slot_init pin_init total_init count_init found_init first_empty_init first_pin_init resident_pins_init live_tokens_init release_matches_init"))
    # Seven reads per resident row; four per live token. Guards can only reduce.
    for k in range(7): add_row(rows,"G2",f"resident_read_{k}",word_load(f"resident_read_{k}"),64,1)
    for k in range(4): add_row(rows,"G2",f"token_read_{k}",word_load(f"token_read_{k}",cast=k>=2),64,1)
    resident_names = "occupied_upper occupied_or pins_limit_field pins_upper pins_or reserved6_test reserved6_or reserved7_test reserved7_if occupied_test occupied_if pins_add pins_store function_limit function_or bytes_zero bytes_or entry_field bytes_upper bytes_if add_receiver add_param_left add_argument add_param_right add_call add_arithmetic add_overflow add_overflow_branch add_Option_tag add_Option_payload add_return_tag add_return_payload add_received_tag add_received_payload add_return_control add_caller_control add_match_tag add_match_branch sum_bind total_store count_add count_store record6_pointer record6_length record6_bound record6_branch record6_scale record6_address record6_load function_equal function_if found_present found_if found_cast found_store empty_function empty_or_1 empty_bytes empty_or_2 empty_pins empty_if first_empty_test first_empty_if empty_cast empty_store slot_add slot_store loop_predicate loop_branch"
    resident_control = [v for v in e("resident_control",resident_names) if not v.startswith("resident_control.add_") and v!="resident_control.sum_bind"]
    resident_control += checked_arithmetic("resident_control.sum","add")
    add_row(rows,"G2","resident_control",resident_control,64,
        note="Conservative union of occupied/empty mutually exclusive arms; return/reject construction belongs to G7, not omitted or borrowed here.")
    token_names = "entry_absent entry_branch nonce_nonzero nonce_branch first_pin_test first_pin_branch first_pin_cast first_pin_store slots_field entry_limit entry_or nonce_zero nonce_or prior_q_pointer prior_q_length prior_q_bound prior_q_branch prior_q_scale prior_q_address prior_q_load prior_q_field nonce_limit nonce_or_2 resident_occupied resident_or resident_pins resident_branch live_add live_store kind_pointer kind_length kind_bound kind_branch kind_scale kind_address kind_load kind_test kind_and nonce_record_pointer nonce_record_length nonce_record_bound nonce_record_branch nonce_record_scale nonce_record_address nonce_record_load nonce_equal nonce_if release_add release_store pin_add pin_store loop_predicate loop_branch"
    add_row(rows,"G2","token_control",e("token_control",token_names),64)
    timestamp_store = call("timestamp_store.to_le_bytes",1,["timestamp_store.LE"],0)+index("timestamp_store")
    add_row(rows,"G2","timestamp_store",timestamp_store,64,2,
        "Exactly64 direct resident-or-tail timestamp array assignments; two distinct array-return/destination copies per store. No Range, st or copy_from_slice call.")
    a_seed = e("A_seed","occupied_equal short_circuit pins_zero condition_branch selected_cast value_binding") + index("A_seed") + ["A_seed.store"]
    b_seed = ["B_seed.offset"] + index("B_seed") + e("B_seed","literal_value store")
    add_row(rows,"G2","A_seed",a_seed,64)
    add_row(rows,"G2","B_seed",b_seed,64)
    add_row(rows,"G2","tail_control",e("tail_control","tail_guard tail_branch slot_add slot_store"),64,
        note="Extra union bound: pays64 tail controls even though resident+tail bodies total64.")
    coherence = e("coherence","release_upper release_if")
    for k in (8,8,6,7,8,9):
        coherence += [f"coherence.q_{len(coherence)}.{v}" for v in "pointer length bound branch scale address load field".split()]
    coherence += e("coherence","resident_pins_equal resident_pins_or live_tokens_equal pins_if count_equal count_or total_equal total_or pins_field pins_limit pins_or nonce_zero nonce_if resident_final_guard resident_final_branch token_final_guard token_final_branch tail_final_guard tail_final_branch")
    add_row(rows,"G2","coherence",coherence)
    # G3: complete one-time call/view chain plus all pair comparisons.
    add_row(rows,"G3","merge_view",view("merge_view",True,True))
    cmp=[]
    for k in ("a","b"):
        cmp += ["cmp."+k+".offset"] + index("cmp."+k) + e("cmp."+k,"byte_read binding")
    cmp += e("cmp","b_MAX b_short_circuit a_present a_short_circuit")
    for k in ("ta","tb"):
        cmp += ["cmp."+k+".cast"]+index("cmp."+k)+e("cmp."+k,"LE scalar_return")
    cmp += ["cmp.timestamp_le"]
    add_row(rows,"G3","comparison",cmp,321,2)
    # G4: all control and scalar byte assignments, no payload-copy movement.
    transfer=e("output","loop_test loop_branch left_exhausted left_branch right_exhausted right_branch take_left_binding chosen_side_branch")
    transfer += ["output.RHS.offset"]+index("output.RHS")+["output.byte_read"]
    transfer += ["output.LHS.offset"]+index("output.LHS")+["output.byte_store"]
    transfer += e("output","side_add side_store out_add out_store")
    add_row(rows,"G4","output",transfer,384)
    add_row(rows,"G4","initial",e("initial","src dst width"))
    add_row(rows,"G4","outer_guard",e("outer_guard","predicate branch"),7)
    add_row(rows,"G4","base_init",["base.init"],6)
    add_row(rows,"G4","base_guard",e("base_guard","predicate branch"),69)
    add_row(rows,"G4","halves",e("halves","left base_plus_width mid twice_width base_plus_twice_width end right out"),63)
    add_row(rows,"G4","output_final",e("output_final","predicate branch"),63)
    add_row(rows,"G4","base_store",["base.store"],63)
    add_row(rows,"G4","swap",e("swap","old_src src dst"),6)
    add_row(rows,"G4","width",e("width","double store"),6)
    # G5 complete exact prefix region and feasibility expression.
    add_row(rows,"G5","prefix_view",view("prefix_view"))
    init = e("prefix_initial","capacity_field base_field capacity_minus_base record13_pointer record13_length record13_bound record13_branch record13_scale record13_address record13_load minus_request headroom_binding remaining_binding mask_binding destination_binding resident_base_div resident_base_binding i_binding")
    add_row(rows,"G5","prefix_initial",init)
    body = e("prefix","remaining_le short_circuit destination_present early_break_branch byte_offset") + index("prefix.byte") + e("prefix","byte_read byte_binding byte_MAX MAX_break_branch slot_zero_extend slot_binding")
    body += word_load("prefix.row",True)
    body += e("prefix","sub_receiver sub_param_left sub_argument sub_param_right sub_call sub_arithmetic sub_underflow sub_underflow_branch sub_Option_tag sub_Option_payload sub_return_tag sub_return_payload sub_received_tag sub_received_payload sub_return_control sub_caller_control sub_match_tag sub_match_branch next_binding remaining_store mask_shift mask_or mask_store destination_store i_add i_store loop_test loop_branch")
    body = [v for v in body if not v.startswith("prefix.sub_") and v!="prefix.next_binding"] + checked_arithmetic("prefix.next","sub")
    add_row(rows,"G5","prefix_iteration",body,64,1)
    add_row(rows,"G5","prefix_finish",e("prefix_finish","loop_final_test loop_final_branch destination_present short_circuit remaining_le feasible_binding"))
    caps={"G2":2560,"G3":2568,"G4":768,"G5":640}
    totals={}
    for owner,cap in caps.items():
        mine=[r for r in rows if r["owner"]==owner]
        scalars=sum(r["scalar_total"] for r in mine)
        copies=sum(r["copy_groups"] for r in mine)
        totals[owner]=dict(scalars=scalars,scalar_groups=(scalars+15)//16,copy_groups=copies,
            groups=(scalars+15)//16+copies,cap=cap)
        assert totals[owner]["groups"] <= cap, totals[owner]
    return dict(schema=1,scope="Exact proposed non-test G2 probes/seeding, full G3/G4 merge, full G5 prefix; no G1/G6/G7 acceptance",rows=rows,totals=totals,
        copy_primitive_max_bytes=128,scalar_block_max=16,source_accounting_accepted=False,
        compiler_or_runtime_qualified=False,group_assignment="owner:S0001... packs the ordered scalar stream in16s; owner:C0001... assigns one actual8-byte movement each; no owner sharing")

def custody():
    receipts=[]
    wanted=[(C3/"candidate-repo-seal.json","7044a00eef658d8c729e7301c0923ed193ec405c6c6009989a964b3159bad12f"),
        (REPO/"verification/swift-cache-state-g3-proposal3/seal.json","8bacc0355f35b504889784313ce070365f347262908bd3d416f26b2b6e11aa0b"),
        (REPO/"verification/swift-cache-state-g3-proposal4/seal.json","70beb0e18af675ff2213eade75f98bfdaf15cc4337ff00dfcca9201414705caa")]
    for path,expected in wanted:
        b=path.read_bytes(); assert digest(b)==expected,(path,digest(b))
        j=json.loads(b)
        # Seals use repository-relative member paths; verify exactly those bytes.
        rows=j.get("members",j.get("files",[]))
        assert isinstance(rows,list)
        for row in rows:
            member=REPO/row["path"]
            if not member.exists(): member=path.parent/row["path"]
            data=member.read_bytes()
            assert len(data)==row["bytes"] and digest(data)==row["sha256"],member
        receipts.append(dict(path=str(path.relative_to(REPO)),sha256=expected,verified_members=len(rows)))
    return receipts

def group_assignment(ledger):
    """Explicit injective assignment of all upper-inventory events to owners.

    Static inventory order is for presentation. For an actual path, filter to
    executed IDs, order by execution, and use the same16-event packing rule.
    A conservative union can only have at least as many events as that path.
    """
    groups=[];seen=set()
    for owner in ledger["totals"]:
        stream=[];copies=[]
        for row in ledger["rows"]:
            if row["owner"]!=owner:continue
            for occurrence in range(row["multiplicity"]):
                prefix=f"{owner}/{row['site']}/{occurrence}"
                stream += [prefix+"/"+name for name in row["scalar_events"]]
                copies += [prefix+f"/payload_{k}" for k in range(row["copies_per_instance"])]
        for k in range(0,len(stream),16):
            ids=stream[k:k+16]
            assert not (seen & set(ids));seen.update(ids)
            groups.append(dict(id=f"{owner}:S{k//16+1:04}",owner=owner,scalar_events=ids))
        for k,event in enumerate(copies):
            assert event not in seen;seen.add(event)
            groups.append(dict(id=f"{owner}:C{k+1:04}",owner=owner,copy_event=event,copy_bytes=8))
        mine=[g for g in groups if g["owner"]==owner]
        assert len(mine)==ledger["totals"][owner]["groups"]
    assert len({g["id"] for g in groups})==len(groups)
    assert all(len(g.get("scalar_events",[]))<=16 and g.get("copy_bytes",0)<=128 for g in groups)
    return dict(schema=1,static_upper_inventory_assignment=groups,event_count=len(seen),
        every_event_has_exactly_one_owner_and_group=True,actual_path_rule="filter to executed IDs; stable order by actual execution; pack within each owner into16s; copy IDs remain distinct",
        no_cross_group_spare=True)

def assemble():
    old=(C3/"source/library/cache_state.rs").read_text()
    assert digest(old.encode())=="0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8"
    merge=(ROOT/"source/merge.rs.txt").read_text().split("fn merge",1)[1]
    merge="fn merge"+merge
    start=old.index("fn merge("); end=old.index("#[cfg(test)]\nstatic COMMIT_FAULT",start)
    new=old[:start]+merge+old[end:]
    start=new.index("    // Shared one-pass bounded probes;")
    end=new.index("    let body = w[6] as usize;",start)
    new=new[:start]+(ROOT/"source/probes.rs.txt").read_text()+new[end:]
    start=new.index("            // The preceding checked base+request guard")
    end=new.index("            sq(c, 10, mask);",start)
    new=new[:start]+(ROOT/"source/prefix.rs.txt").read_text()+new[end:]
    # Exact cleanup and all other suffix bytes are preserved, not re-authored.
    marker="fn cleanup("
    assert marker in old
    assert old[old.index(marker):]==new[new.index(marker):]
    # No cfg-test counters removed or extra external APIs/owners introduced.
    assert old.count("SORT_COMPARISONS.fetch_add")==new.count("SORT_COMPARISONS.fetch_add")==1
    assert old.count("SORT_MOVES.fetch_add")==new.count("SORT_MOVES.fetch_add")==1
    (ROOT/"source/cache_state.rs.txt").write_text(new)
    (ROOT/"proposed.diff").write_text("".join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile="C3/cache_state.rs",tofile="PROPOSED/cache_state.rs")))
    return dict(base_sha256=digest(old.encode()),proposed_sha256=digest(new.encode()),
        cleanup_and_suffix_sha256=digest(old[old.index(marker):].encode()),cleanup_and_suffix_identical=True,
        changed_regions=["G2 resident/token probes and seeding","whole private merge","G5 selected prefix"],
        compiled=False,executed=False)

def merge_model(times, seed):
    # Model byte indices, deliberately separate from source text/any Rust parser.
    arena=[255]*1536;arena[:64]=seed
    src,dst,width=0,512,1; comparisons=0; moves=0; tests=[]
    while width<64:
        base=0;per_pass=0
        while base<64:
            left=base;mid=base+width;end=base+2*width;right=mid;out=base
            while out<end:
                if left==mid: take=False
                elif right==end: take=True
                else:
                    assert base<=left<mid<=right<end<=64
                    a=arena[src+left];b=arena[src+right];comparisons+=1;per_pass+=1
                    take=b==255 or (a!=255 and times[a]<=times[b])
                chosen=left if take else right
                assert 0<=src+chosen<576 and 0<=dst+out<576
                assert (src<64 and dst>=512) or (dst<64 and src>=512)
                arena[dst+out]=arena[src+chosen]
                if take:left+=1
                else:right+=1
                out+=1;moves+=1
            base=end
        tests.append(per_pass)
        src,dst=dst,src;width*=2
    assert moves==384 and comparisons<=321 and src==0
    return arena[:64],dict(comparisons=comparisons,moves=moves,pass_comparisons=tests)

def prefix_model(order, bytes_by_slot, base, capacity, request, total, first_empty):
    assert base+request<=capacity
    remaining=total;mask=0;destination=first_empty;headroom=capacity-base-request
    chosen=[]
    for byte in order:
        if remaining<=headroom and destination!=(1<<64)-1: break
        if byte==255:break
        assert 0<=byte<64
        assert remaining>=bytes_by_slot[byte]
        remaining-=bytes_by_slot[byte];mask|=1<<byte;destination=byte;chosen.append(byte)
    return dict(remaining=remaining,mask=mask,destination=destination,
        feasible=destination!=(1<<64)-1 and remaining<=headroom,chosen=chosen)

def checks():
    rng=random.Random(0xB17E2048);cases=0;max_cmp=0;pass_max=[0]*6
    # Every configured count and every eligible count, genuine MAX timestamps,
    # all tails, unsigned top-bit values and stable duplicates are represented.
    distributions=["ascending","descending","equal","MAX","top_bit","bit_reversal","random"]
    for n in range(1,65):
        for eligible in range(n+1):
            for mode in distributions:
                slots=list(range(n));rng.shuffle(slots);allowed=set(slots[:eligible])
                if mode=="ascending":times=list(range(64))
                elif mode=="descending":times=list(reversed(range(64)))
                elif mode=="equal":times=[7]*64
                elif mode=="MAX":times=[(1<<64)-1]*64
                elif mode=="top_bit":times=[(1<<63)+(i%4) for i in range(64)]
                elif mode=="bit_reversal":times=[int(f"{i:06b}"[::-1],2) for i in range(64)]
                else:times=[rng.choice([0,1,7,(1<<63),(1<<64)-1,rng.getrandbits(64)]) for _ in range(64)]
                seed=[i if i<n and i in allowed else 255 for i in range(64)]
                result,stats=merge_model(times,seed)
                expected=sorted(allowed,key=lambda i:(times[i],i))+[255]*(64-eligible)
                assert result==expected,(n,eligible,mode)
                max_cmp=max(max_cmp,stats["comparisons"])
                pass_max=[max(x,y) for x,y in zip(pass_max,stats["pass_comparisons"])]
                cases+=1
    assert max_cmp==321 and pass_max==[32,48,56,60,62,63], (max_cmp,pass_max)
    prefix_cases=0
    ABSENT=(1<<64)-1
    for n in range(1,65):
        for empty in [ABSENT,63]:
            order=list(range(n))+[255]*(64-n)
            weights={i:(i%7)+1 for i in range(n)};total=sum(weights.values())
            for headroom in range(total+1):
                actual=prefix_model(order,weights,0,headroom+1,1,total,empty)
                # Independent repeated-prefix oracle, using no merge model.
                k=0
                while k<n and (total-sum(weights[i] for i in range(k))>headroom or (empty==ABSENT and k==0)):
                    k+=1
                expected_destination=(k-1 if k else empty)
                assert actual["chosen"]==list(range(k))
                assert actual["destination"]==expected_destination
                assert actual["feasible"]==(expected_destination!=ABSENT and actual["remaining"]<=headroom)
                prefix_cases+=1
    # Address/alignment arithmetic is finite and depends on layout, not ABI.
    analyzer=(C3/"source/library/analyzer.rs").read_text()
    envelope=(C3/"source/library/envelope.rs").read_text()
    assert "type Candidate2048 = [u8; 2048];" in envelope
    # Conservative structural source facts supplement, never replace, models.
    assert "const RESIDENT" in analyzer and "const PIN" in analyzer
    assert "base: 7_680_000, rows: 64, stride: 64" in analyzer
    assert "base: 7_684_096, rows: 64, stride: 48" in analyzer
    for row in range(64):
        for field in range(8):
            at=7_680_000//8+row*8+field
            assert at*8==7_680_000+row*64+field*8 and at<8_388_608//8
        for field in range(6):
            at=7_684_096//8+row*6+field
            assert at*8==7_684_096+row*48+field*8 and at<8_388_608//8
    # Candidate-only cleanup model: arbitrary old envelope payload/padding is
    # never interpreted as a byte index. Every byte clears, then exact restores.
    restore_cells=[7,9,10,11,12,13,14,64,65,66,160,161]
    assert len(set(restore_cells))==12
    cleanup_cases=0
    for n in range(1,65):
        c=bytearray(rng.getrandbits(8) for _ in range(2048))
        original=c[:]
        for slot in range(64):
            c[slot*8:slot*8+8]=((1<<64)-1 if slot<n else 0).to_bytes(8,'little')
            c[512+slot]=slot if slot<n else 255
            c[1024+slot]=255
        assert c[576:1024]==original[576:1024] and c[1088:1536]==original[1088:1536]
        payload=[rng.getrandbits(64) for _ in restore_cells]
        for start in range(0,2048,128):c[start:start+128]=bytes(128)
        for k,value in enumerate(payload):c[888+k*8:896+k*8]=value.to_bytes(8,'little')
        assert not any(c[:888]) and not any(c[984:])
        assert c[888:984]==b''.join(v.to_bytes(8,'little') for v in payload)
        cleanup_cases+=1
    return dict(sort_cases=cases,prefix_cases=prefix_cases,max_comparisons=max_cmp,
        max_moves=384,per_pass_comparison_maxima=pass_max,unsigned_MAX_and_top_bit=True,
        all_configured_limits_and_eligible_counts=True,source_model_only=True,
        compiler_or_runtime_execution=False,arena_address_field_cases=64*(8+6),candidate_padding_cleanup_cases=cleanup_cases)

def main():
    assert ROOT.name=="swift-cache-state-byte-index-proposal"
    identities=custody()
    assembly=assemble()
    ledger=build_ledger()
    assignment=group_assignment(ledger)
    models=checks()
    write_json(ROOT/"custody.json",identities)
    write_json(ROOT/"source-assembly.json",assembly)
    write_json(ROOT/"operation-ledger.json",ledger)
    write_json(ROOT/"group-assignment.json",assignment)
    write_json(ROOT/"model-results.json",models)
    result=dict(status="source-only checks passed",ledger=ledger["totals"],models=models,
        source_accounting_accepted=False,lifetime_proof_accepted=False,independent_accepted=False,
        native_or_capture_started=False,GA_qualified=False)
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":main()
