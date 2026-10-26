#!/usr/bin/env python3
"""Generate independent preaccess design data from OWN frozen inputs only.

This is not a product test. It cannot access a candidate or producer harness.
"""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROSTER = HERE / "inputs/verification/android-private-owner-effect-roster-amendment/required-host-roster.json"
CASES = ["clean", "terminal-at-entry", "terminal-before-return", "dirty-at-entry",
         "dirty-before-return", "ordinary-throw-after-callback", "fatal-throw-after-callback"]


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n")


def family(code, name, subjects, setup, stimulus, observations, forbidden, positives, variants=None):
    return dict(id=code, name=name, actual_subjects=subjects.split(), setup=setup,
                stimulus=stimulus, observe=observations, forbidden=forbidden,
                positive_control=positives, variants=variants or [],
                execution_status="not-run-preaccess-design")


def main():
    r = json.loads(ROSTER.read_text())
    custody = json.loads((HERE / "input-custody.json").read_text())
    inputs = {x.get("candidate_path", x["path"]): x for x in custody["allowed_inputs"]
              if x["source"] == "git-object-accepted-baseline"}
    rows = []
    for site in r["baseline_callback_barriers"] + r["v1_compile_baseline_only"]:
        item = copy.deepcopy(site)
        path = HERE / inputs[site["source"]]["snapshot"]
        data = path.read_bytes()
        lines = data.decode().splitlines(keepends=True)
        line = lines[site["line"] - 1].rstrip("\r\n")
        assert line.strip() == site["source_line"]
        assert line[site["column"] - 1:].startswith(site["expression"])
        same = sorted([x for x in r["baseline_callback_barriers"] + r["v1_compile_baseline_only"]
                       if (x["source"], x["line"]) == (site["source"], site["line"])],
                      key=lambda x: x["column"])
        item.update(baseline_source_sha256=hashlib.sha256(data).hexdigest(),
                    baseline_byte_offset=len("".join(lines[:site["line"] - 1]).encode()) +
                    len(line[:site["column"] - 1].encode()),
                    same_line_selected_ordinal=next(i + 1 for i, x in enumerate(same) if x["id"] == site["id"]),
                    same_line_selected_count=len(same),
                    expression_occurrence_on_line=line[:site["column"] - 1].count(site["expression"]) + 1,
                    candidate_binding=None,
                    binding_status="pending-root-candidate-admission")
        if site in r["baseline_callback_barriers"]:
            item["independent_case_ids"] = [site["id"] + "/" + case for case in CASES]
        else:
            item["independent_case_ids"] = [site["id"] + "/v1-positive-unchanged"]
        rows.append(item)
    write("site-input-map.json", dict(schema=1, baseline_revision=custody["baseline_revision"],
          status="preaccess-baseline-only", v2_baseline_sites=rows[:184], v1_baselines=rows[184:],
          new_candidate_sites=None, new_site_gate="explicit candidate source/BCI audit after root admission; never empty by assumption",
          concrete_subjects=r["closures"]["B-concrete-renderer-views"]["actual_production_sources"],
          concrete_substitute_roster=r["closures"]["B-concrete-renderer-views"]["substitutes"],
          orchestration_closure=r["closures"]["A-orchestration"],
          candidate_subject_hashes=None, leaf_reuse_admitted=False))
    f = []
    add = lambda *a, **kw: f.append(family(*a, **kw))
    add("I01", "Inert allocation and exact publication", "NativeOwnerV2 NativeCoordinatorV2 NativeEnvironmentV2 OwnerLifecycleV2",
        "Construct owner with one Activity/private root; retain references before start.",
        "Observe constructors; invoke start with first-registration synchronous detach and create-return terminal reentry.",
        ["Zero JNI create/listener adds in bookkeeping constructors", "Observer is stored before first add callback", "Opening coordinator retained before renderInitial acquisition", "Late acquired coordinator closes once after return and is never published live"],
        ["Lazy renderer observer acquisition", "Unheld acquired coordinator", "Disposal during active create frame"], "Ordinary ready start creates exactly one session and publishes only after finish/completion.")
    add("I02", "Actual main Looper before stale guards", "NativeOwnerV2 NativeCoordinatorV2 NativeEnvironmentV2 NativeRenderer",
        "Live and retired instances; owned/stale runnable and report identities.", "Invoke every admitted package/public entry with non-main Looper facts.",
        ["Thread rejection precedes stale/retired early return", "No listener/JNI/queue/gate mutation before rejection"],
        ["Injected product thread predicate", "Stale delivery bypassing main check"], "Same entry on main proceeds or is inert according to actual state.")
    add("I03", "Concrete readiness and focus mapping", "NativeOwnerV2 OwnerLifecycleV2 NativeEnvironmentV2",
        "Unattached, null Window/token, zero width/height or null insets root, then independently ready facts.",
        "Deliver actual observer notifications and one manually drained Handler delivery; change focus on start, notification and drain.",
        ["No create while not ready", "No polling or self-repost", "Fresh delivery reads Activity/Window/token/size/insets/focus", "focusKnown initial seeding and changed focus reach real core.focusChanged before input", "Unchanged focus notification still invalidates once", "Only same observer owns focus listener", "resume/pause/stop use actual core entries"],
        ["Read-but-unused focus", "Second readiness/focus/inset listener", "Manufactured identity for a desired reason"], "Ready foreground focused presentation admits input; unfocused/background preserves readiness but rejects input.")
    add("I04", "All eight registration slots and unwind", "NativeOwnerV2 NativeEnvironmentV2 OwnerLifecycleV2",
        "Actual two-phase Observer and mechanical Android targets; fixed per-slot counters and listener identities.",
        "At each add: ordinary throw, fatal throw, synchronous detach, and add-then-throw; at each remove: return, ordinary/fatal throw, dead focus target, recursive close.",
        ["NEW constructor has zero adds", "Callbacks assigned before first add", "Before-add possibly-owned claim", "No later acquisition after retirement", "Exact targets used for all removals", "Acquiring slot cleanup waits until add unwinds", "Owner unregister completion is deferred during registration", "Eight independent retained outcomes, borrowed report identity", "Repeated close does not retry consumed slots"],
        ["Returned means OS reclaimed", "Outer reentrant close falsely completes unregister", "Unbounded failure history"], "All eight successful adds and removals use exact stored targets once.", list(range(8)))
    add("I05", "Once binding and capture provenance", "NativeEnvironmentV2 NativeRenderer InstalledAppearanceV2",
        "Two owners with distinct Activity/private roots and separately registered observers.",
        "Capture/register/bind out of order; null/foreign/repeated renderer binding; capture after retirement or tuple/generation/window changes.",
        ["Bind READY-only and exactly once including same identity", "Capture uses exact bound renderer/context", "Second concrete tuple read and generation reject stale authority", "Installed belongsTo uses real capture owner"],
        ["Caller-created trusted environment", "Two inset owners on one root"], "Correct registered/bound renderer captures through actual installed/environment bodies.")
    add("I06", "Exact operation publication and completion", "NativeOwnerV2 OwnerLifecycleV2 NativeCoordinatorV2 NativeRenderer",
        "Real core-issued lifetime, drain, operation and presentation tokens; opening and adopted coordinator identities.",
        "Callback at coordinator entry, candidate preparation, attach and finish; inject foreign/stale/repeated completion and terminal late acquisition.",
        ["Exact operation stored in shared fence before coordinator entry", "Candidate stores same non-null identity", "Completion only exact operation/coordinator after finish and active=false", "No publication before successful finish", "Foreign/stale completion inert", "No replacement token adopted after reentry"],
        ["Forged core token", "Draw/input flags authorize transaction mutation", "Completing failed work as committed"], "Clean transaction finishes and publishes exact real-core presentation.")
    add("I07", "Early virtual construction and prepublication barriers", "NativeRenderer NativeAppearanceViewsV2",
        "Actual Record/Gate and all actual native subclasses; constructor hooks enter overrides before record fields are assigned.",
        "Exercise every mandatory early virtual entry and seven-case native constructor/default/text/child-add sites before v2Pending exists.",
        ["Unassigned-record override is inert and returns without subsequent superclass mutation", "Record stores fence before native construction", "After constructor callback original scope is validated before next Mixer setter", "Actual absent/present pending/current flags recorded honestly"],
        ["Product callback from uninitialized override", "Only checking after entire bind", "Claiming framework internals interrupted"], "Actual constructor/default/child-add paths complete under a valid transaction.", r["early_virtual_constructor_entries"])
    add("I08", "Complete concrete call-site matrix", "NativeRenderer NativeAppearanceViewsV2 NativeOwnerV2 NativeCoordinatorV2 NativeEnvironmentV2",
        "Actual fourteen-subject closure; valid decoded packet/descriptor; explicit BCI/source site map.",
        "For every baseline and new site execute all seven sealed variants at exact leaf entry/before-return positions.",
        ["Reached exact method descriptor and BCI", "Actual shared/current/pending gates at callback entry and after seal", "No next forbidden Mixer mutation/commit/event after terminal/fatal", "Cleanup-only effects separately labeled", "Lifecycle-only and observer-generation dirty stimuli distinguished", "Each row retains its own result and call deltas"],
        ["Wildcard method-name coverage", "Coarse faultV2 substitute", "Compile-only or scripted renderer flags counted as concrete"], "Each exact site has a separately reached clean control.", CASES)
    add("I09", "Dirty type and timing clarification", "NativeEnvironmentV2 NativeOwnerV2 OwnerLifecycleV2 NativeCoordinatorV2 NativeRenderer",
        "Capture generation G; exact real-core operation T; distinct observer and lifecycle callbacks.",
        "Compare lifecycle-only dirty with actual observer.invalidate before capture, after capture before validation, attach/layout, precommit, refresh, input and admitted JNI timing.",
        ["Lifecycle-only unchanged capture can finish, complete true, stay dirty and queue one later drain", "Observer increments generation before sink", "When remaining validation sees G stale, reject and retire through actual failed-operation path", "Before-capture case can use later fresh capture", "No general claim that every after-capture site is followed by a concrete validation", "Idle current mismatch seals and schedules through same observer without invented renderer reason"],
        ["Weakened generation/tuple checks", "Silent recapture/retry or forged successful completion", "Replacing actual observer case with lifecycle case", "Added capture between successful commit and finish"], "No dirty callback leaves a clean committed presentation; unchanged capture dirty control demonstrates single drain.")
    add("I10", "Immutable transaction/live/cleanup scopes", "NativeAppearanceViewsV2 NativeRenderer NativeOwnerV2",
        "Scope captures exact T or P before native work; actual recursive measure/layout/title helpers.",
        "Replace current token via genuine operation/presentation transition during a callback; enter transaction-generated and cleanup-generated callbacks.",
        ["Recursive helpers pass same scope reference", "No recapture after invalidation", "Group layout uses retained transaction scope", "Programmatic setter callback sends no feature event", "Cleanup scope only consumed release/hide work", "Expired P0 never borrows P1"],
        ["Mutable mode/token", "Cleanup binds/layouts or opens input", "Transaction callback treated as ordinary input"], "Valid transaction mutations succeed while draw/input are intentionally false.")
    add("I11", "Positive live callbacks with no operation", "NativeAppearanceViewsV2 NativeRenderer AuthoredToggleInputV2",
        "Actual committed clean focused foreground presentation; fence.operation is null.",
        "Scroll navigation through collapse/expand, gesture arbitration, key/accessibility and ordinary text/toggle input.",
        ["Real current presentation authorizes ordinary callbacks without an operation token", "Actual header/compact/child relayout reaches concrete helpers", "One actual event per accepted action", "Focus/current-record/disabled/toggle binding checks retained"],
        ["Fabricating operation token for normal callbacks", "Programmatic setters generate feature events"], "Normal native scrolling/navigation/IME/gesture stays usable.")
    ime = ["commitText/2", "commitText/3", "setComposingText/2", "setComposingText/3", "setComposingRegion/2", "setComposingRegion/3", "finishComposingText", "deleteSurroundingText", "deleteSurroundingTextInCodePoints", "setSelection", "performEditorAction", "sendKeyEvent", "setImeConsumesInput", "commitCompletion", "replaceText", "performPrivateCommand", "performHandwritingGesture", "previewHandwritingGesture", "commitCorrection", "commitContent"]
    add("I12", "Actual IME acquisition and every forwarding family", "NativeAppearanceViewsV2 NativeRenderer NativeOwnerV2 NativeCoordinatorV2 UiPacket",
        "Real NativeField, wrapper and Editable; actual TextWatcher/owner/coordinator transaction commits successor P1 synchronously within P0 delegate.",
        "For each forwarding family test actual successor; nonforwarding overrides get explicit refusal and zero-forward controls. Both retain exact-current, dirty, terminal and stale/foreign controls; fatal is exercised wherever a selected call is reachable. Acquire new connection while sealed and use retained connection after sealing; no site/case row is removed.",
        ["Sealed acquisition returns null before superclass acquisition", "Sealed retained wrapper calls zero mutating delegates", "Each delegate entry validates immutable captured scope", "Clean successor-only completed result returns immediately using scalar/reference checks", "No further native/capture/event/mutation after expired scope", "Terminal/dirty result rejects and Error escapes", "Next independent invocation captures its own valid scope and concrete record/focus", "Unsupported families keep explicit refusal and allowed diagnostic callbacks"],
        ["Canned result alone proves real successor", "Postdelegate recapture of P1", "Expired P0 seals legitimate P1 merely for being stale", "Exception swallowing hides Error"], "Actual commitText triggers real decoded event, one input transaction and successor before returning its completed result.", ime)
    add("I13", "Seal serial progression and exhaustion", "NativeOwnerV2 NativeCoordinatorV2 NativeRenderer",
        "Actual serial starts at one; admitted test seed/reflection sets counter near Long.MAX_VALUE only.",
        "Dirty/terminal callbacks, repeated same-serial cancellation and exhaustion at maximum.",
        ["Terminal bit first; shared/current/pending flags close before callbacks", "Serial advances before callback", "MAX never wraps/resets", "Exhaustion retains SEAL_SERIAL_EXHAUSTED and requests unchanged core.close", "Late coordinator sealed at current serial"],
        ["Zero/reset claim revives work", "Allocating/iterating scalar seal", "Exhaustion skips independent cleanup"], "Distinct nonrecursive seals may authorize distinct bounded cancellation passes.")
    add("I14", "Stable bounded cancellation rosters", "NativeRenderer NativeAppearanceViewsV2 NativeCoordinatorV2",
        "Actual current/pending-target/pending-detached rosters, duplicate record across all three and 4096-node bounds.",
        "Cancel during active transaction; first/middle/last Record throws ordinary/fatal; recursive new dirty/terminal serial at cancellation leaf.",
        ["At most 12288 references", "Roster references/counts captured at pass entry", "Consumed serial and per-record claim precede callback", "All distinct remaining records attempted despite failures", "Recursive request does not restart cursor/rebuild roster", "No transaction replaces rosters during pass", "Retained fixed ledger, no iterator/list growth"],
        ["Active-safe bridge enter/dispose/create/destroy/commit", "Duplicate identity cancelled twice in same pass", "Recursive return counted as completed parent release"], "Stable duplicate-free bounded scan attempts every record once per consumed pass.")
    add("I15", "clearTouch independent native cleanup", "NativeAppearanceViewsV2 AuthoredToggleInputV2",
        "Actual NativeSwitch has active touch and retained parent; distinct first/middle/last failure identities.",
        "Fail setPressed(false), invalidate and requestDisallowInterceptTouchEvent(false) independently, including recursive drawable/lifecycle callbacks.",
        ["Touch and parent ownership consumed before first callback", "All three release attempts independent", "Parent release at most once", "No paint/bind/layout resumes in cleanup/terminal callback", "setEnabled/setFrame cancel then revalidate original scope before super"],
        ["Returned proves parent released", "First failure skips later releases", "finally reconciliation emits feature input after seal"], "Normal valid gesture cancels cleanly and actual toggle path still emits one accepted event.")
    add("I16", "First primary and first fatal identities", "NativeOwnerV2 NativeCoordinatorV2 NativeRenderer NativeEnvironmentV2",
        "Distinct ordinary A/B and Error E; suppression-disabled primary and multiple independent cleanup faults.",
        "Ordinary primary followed by Error in cancellation/unregister/dispose/destroy; repeat reports and additional later errors.",
        ["First primary and first fatal retained independently before suppression", "Every independent cleanup attempted", "First fatal E escapes after attempts", "No allocation/traversal needed to discover E", "Later report arguments cannot replace first cause or retry consumed cleanup"],
        ["Fatal swallowed by false current result", "Primary-only graph traversal controls fatal", "Unbounded exception log"], "Ordinary live report does not automatically throw its reported ordinary primary; originating API preserves throw policy.")
    add("I17", "Single exact typed renderer report", "NativeRenderer NativeEnvironmentV2 NativeOwnerV2 OwnerLifecycleV2",
        "Actual bound renderer/observer plus foreign renderer/observer and wrong-thread facts.",
        "Emit first report, repeat, stale retired report, foreign live report and reentrant cleanup report.",
        ["Main checked first", "Live foreign source/cause rejects before diagnostic acceptance", "Renderer claims and scalar-seals before route", "Observer claims and retires before sink", "Owner terminalProcessed is distinct from shared terminal", "Exactly one Sink route and core transition", "Stale report supplied failures ignored while originating observed Error still escapes"],
        ["Ordinary input event terminal channel", "Second owner listener", "Already-set terminal suppresses required core transition", "Dispose reports recursively"], "Exact first live report processes cause once and preserves real core CLOSED versus detailed adapter cause.")
    causes = ["INTERACTION_EXHAUSTED", "CAPTURE_FAILED", "ROLLBACK_FAILED", "CURRENT_CHECK_FATAL", "CANCELLATION_FAILED", "TERMINAL_VALIDATION_FAILED"]
    add("I18", "Actual self-retirement causes", "NativeRenderer NativeAppearanceViewsV2 NativeEnvironmentV2 NativeOwnerV2 NativeCoordinatorV2",
        "Actual interaction counter, installed/environment capture paths, rollback and Gate/Input current bodies.",
        "Independently trigger every typed cause through originating actual API, including RuntimeException and Error variants.",
        ["Interaction exhaustion has no manufactured exception", "Capture and rollback retain exact failures", "Fatal current Error reports CURRENT_CHECK_FATAL and escapes", "Cancellation reports only after bounded attempts", "Direct terminal validation has exact cause", "Ordinary tuple mismatch dirties and is not relabeled terminal"],
        ["Test directly calls report instead of demonstrating originating failure", "Cause manufactured to satisfy expected core reason"], "Ordinary current tuple match and live input/draw succeed.", causes)
    add("I19", "Single work slot and unwind tail", "NativeOwnerV2 NativeCoordinatorV2 OwnerLifecycleV2 NativeRenderer",
        "One owned Handler slot tagged DRAIN or TERMINAL_CLOSE; real main Handler modeled as never inline.",
        "Terminal report from owner effect versus idle native draw/input; duplicate/stale deliveries; report/cancel/active frames block close.",
        ["Consume ordinary drain before posting terminal tail", "At most one concurrent owned runnable", "Tail carries exact close token/resource or explicit unreported fallback", "Dispose only after report/cancel/transaction frame exits", "Stale delivery cannot consume newer slot", "Post false/throw leaves detailed pending disposition"],
        ["Second cleanup runnable", "Polling or retry", "Reentrant disposal to claim complete"], "Manually delivered terminal tail disposes once after originating callback stack returns.")
    add("I20", "Post/cancel failure and stale deliveries", "NativeOwnerV2 OwnerLifecycleV2",
        "Bounded mechanical queue with exact runnable identities and saved stale delivery.",
        "post false, post ordinary/fatal throw, removeCallbacks ineffective/throwing, stale callback after a newer drain exists.",
        ["Claim/consume slot before external post/remove", "Terminal scheduling failure retained", "Independent unregister/cancel proceeds", "Exact token delivery only", "No rejected event retained"],
        ["Retry on post failure", "Removal return proves undeliverable", "Stale delivery steals latest token"], "Burst notifications coalesce one queued drain and fresh probe consumes it once.")
    add("I21", "Deferred close, late acquire and nonreturning work", "NativeOwnerV2 NativeCoordinatorV2 OwnerLifecycleV2",
        "Bounded latch inside actual operation leaf; opening factory local and adopted resource identity may alias.",
        "Terminal during create/prepare/attachment/input/refresh/cancel/report; inspect pending before latch release, then release in finally.",
        ["Cancel/unregister independent while operation active", "No close while busy", "Late acquire completes exact original operation then one close", "Aliased opening/adopted resource attempted once", "If work not returned at observation, disposition explicitly pending"],
        ["Timer fabricates completion", "Unbounded host thread retained", "Direct close while JNI/render callback active"], "After real return active=false leads to once-only idle disposal.")
    add("I22", "Successful commit/finish interval", "NativeCoordinatorV2 NativeRenderer NativeOwnerV2",
        "Actual decoded/attached candidate; independently reviewed production source and javap control flow.",
        "Clean status zero; scalar terminal/operation mismatch failure around finish; deferred fatal/cause fields.",
        ["Successful interval has only existing branch/direct call and scalar/reference checks/swaps", "No callback/capture/allocation/core/native mutation", "commitFinish brackets interval with scalar finally", "Deferred route occurs only after flag clears", "Presentation publication after finish and active=false"],
        ["Fault hook inside interval", "finish reports synchronously", "Counted JNI leaf alone proves no callbacks"], "Exact bytes and bytecode reachable body reviewed in addition to successful actual transaction.")
    add("I23", "Exact retained-packet zero-JNI refresh", "NativeCoordinatorV2 NativeRenderer NativeOwnerV2 UiPacket",
        "Committed packet P with recorded reference, byte digest/revision and JNI counters.",
        "Actual dirty drain refresh and dirty during refresh; compare lifecycle-only and generation-stale variants.",
        ["Same coordinator uses exact retained byte[] reference and bytes", "Zero create/exchange/prepare/commit/abort/dispatch/effects or Swift revision advance", "Actual capture/renderer methods still execute", "Successful lifecycle dirty refresh finishes with one later drain", "Stale-capture refresh fails through actual failure path"],
        ["Owner keeps packet copy", "Reconstructed/equal packet substituted", "Fake renderer validates identity alone"], "Real renderer refresh changes environment presentation while JNI counters remain unchanged.")
    add("I24", "Synchronous unbuffered ordinary input", "NativeOwnerV2 OwnerLifecycleV2 NativeCoordinatorV2 NativeRenderer UiPacket AuthoredToggleInputV2",
        "Actual decoded event and valid focused foreground P; distinct rejected envelope byte arrays.",
        "Accepted edit, reentrant edit, background/unfocused/stale/dirty/terminal edits; force ordinary retired rejection and fatal.",
        ["Accepted dispatch operation 1 once before caller returns", "Exact caller bytes only on stack", "No owner packet/event field or backlog", "Rejected bytes never replay after readiness", "Native edits contained only after both relevant owners terminal with failure retained", "Fatal always escapes"],
        ["Queue/retry input", "Direct coordinator native callback bypass", "Reentrant event starts second operation"], "Actual TextWatcher/toggle callback reaches actual owner and counted JNI once.")
    add("I25", "Core allocation/completion fallback", "NativeOwnerV2 OwnerLifecycleV2 NativeCoordinatorV2",
        "Admitted test-only fault seam or exact bounded host allocation fault; real core remains byte-exact.",
        "Throw Error from core decision/token/completion bookkeeping before/after resource acquisition.",
        ["Scalar seal precedes fallback", "Preallocated cancel/unregister/idle disposition attempts independent", "Core-completion-unreported retained without nonexistent cleanup token", "Active resource remains deferred until return", "Later entry cannot revive older core state"],
        ["Core edited to support injection", "Token fabricated for cleanupComplete", "Fault claimed solely by model"], "No-fault real core completes with exact tokens and unchanged bytes.")
    add("I26", "Rollback and independent disposition outcomes", "NativeCoordinatorV2 NativeRenderer NativeAppearanceViewsV2 NativeOwnerV2",
        "Actual pending candidate/journal with prior presentation and faultable restore native calls.",
        "Known reject/abort, unknown commit outcome, rollback/restore failure; renderer dispose and engine destroy independently fail.",
        ["Actual terminal/operation scope checked before every subsequent restore setter", "Terminal rollback never reopens old gates", "session=0 and committedPacket=null published before cleanup", "Consumed renderer/session dispositions not repeated", "Unknown native outcome terminally retained", "Original and cleanup/fatal failures retain identities"],
        ["Second dispose after internal retirement", "One cleanup failure skips another owner", "Returned ledger proves native resource reclaimed"], "Clean admitted rollback preserves valid previous presentation only where contract permits.")
    add("I27", "Real independently authored decoder witnesses", "UiPacket Json AppearanceDescriptorV2 InstalledAppearanceV2 AppearanceResolverV2 AppearanceGeometryV2 AppearanceNativePathsV2 AuthoredToggleInputV2 NativeRenderer NativeAppearanceViewsV2",
        "Sealed independent packet literals and candidate-addendum independent descriptor bytes from frozen grammar; asset stream leaf supplies raw bytes only.",
        "Actual capture/decode/resolve/render/input; malformed revision/identity/schema/resource/font/size/encoding and unsupported-node witnesses.",
        ["Actual complete decoder bodies execute", "Descriptor digest from actual capture", "No native mutation before negative decode rejection", "Positive plan reaches actual geometry/path/view/toggle bodies", "Bytes and expected identities independently recorded"],
        ["Trusted capture/current object minted by leaf", "Imported producer expected objects", "Actual14 counted from class load"], "Valid navigation/list/section/text/field/button/toggle tree lays out and produces a real decoded event.")
    add("I28", "Five unchanged V1 positive baselines", "NativeRenderer UiPacket Json",
        "Actual V1 two-argument renderer and independently authored predecessor/successor tree packets.",
        "Apply/reorder/remove/add/change spacing and hStack margins to reach each exact five historical sites.",
        ["Actual apply/children bodies execute each historical ID", "V1 hierarchy/layout outputs match independent tree expectation", "Complete source compiles", "Public Activity V1 routing and padding bytes unchanged"],
        ["V2 operation/presentation/terminal/dirty requirements imposed on V1", "V1 bypass inserted for host tests"], "Five exact sites retain separate reached positive receipts and no V2 matrix classification.")
    add("I29", "Exact source relocation and closure", "OwnerLifecycleV2 NativeOwnerV2",
        "Admitted source map versus frozen accepted baseline and amended exact rosters.",
        "Hash every actual source/leaf/test; enumerate canonical/export paths; compare 22 SDK, descriptor, wire and public V1 identities.",
        ["Core SHA-256 exactly 4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6", "Core canonical source moved once", "Fourteen actual subjects/73 concrete substitutes", "No broad Android jar/implicit classpath/sourcepath", "New selected calls explicitly mapped with seven rows"],
        ["Source-text guard alone proves behavior", "Extra copied core or hidden product substitute", "Current mutable bytes substituted for admission"], "Complete source map matches root-admitted literals.")
    add("I30", "Profile/cross-build and remaining gates", "NativeOwnerV2 OwnerLifecycleV2 NativeCoordinatorV2 NativeEnvironmentV2 NativeRenderer",
        "Profile ID source-pair.3 selected but hash literals not yet selected.",
        "Check root exact-source-profile selection before any CLI/common/driver/copied-consumer execution; separately inspect official SDK Java/D8/Swift-JNI cross-build receipts.",
        ["22 unchanged SDK identities and exact default descriptor/wire", "22 adapter map if no extra selected source", "Old/edited/recomputed locks rejected before tools/outputs after root hash gate", "Native/runtime/UI/physical/FieldLog/store/GA explicitly pending"],
        ["Silently refresh source-pair.2", "Run consumers before root literal selection", "Host tests qualify public V2 or native reclamation"], "Root-selected exact map has separately labeled consumer/signature evidence; no claim made by preaccess slice.")
    write("cases.json", dict(schema=1, author="independent preaccess review lane", actual_candidate_access=False,
          source_of_expected_behavior="selected contracts, admitted clarification opinion and accepted baseline inspection; no producer test/leaf/probe access",
          families=f, baseline_v2_matrix=[dict(id=x["id"] + "/" + case, site_id=x["id"], variant=case,
                stimulus="exact immutable scope; lifecycle-only versus actual-observer dirty timing recorded separately" if case.startswith("dirty") else case,
                result="not-run-preaccess-design") for x in r["baseline_callback_barriers"] for case in CASES],
          positive_v1=[dict(id=x["id"] + "/v1-positive-unchanged", site_id=x["id"], result="not-run-preaccess-design") for x in r["v1_compile_baseline_only"]],
          required_gate="root selects clarification and admits candidate; later separately audited leaf reuse before product execution"))
    command_root = "verification/android-private-owner-independent-review/preaccess"
    write("commands.json", dict(schema=1, scope="preaccess design only", cwd="/Users/andreyyurlov/Documents/dev/mixer",
          now=[dict(id="generate", argv=["python3", "-B", f"{command_root}/generate_design.py"]),
               dict(id="check-design", argv=["python3", "-B", f"{command_root}/verify_design.py"]),
               dict(id="seal", argv=["python3", "-B", f"{command_root}/seal_preaccess.py", "--seal"]),
               dict(id="verify-seal", argv=["python3", "-B", f"{command_root}/seal_preaccess.py", "--check"])],
          candidate_gate="no future command runnable until root admission and literal argv/source-list/tool digest candidate addendum",
          future_templates=[dict(id="compile", argv=["<admitted-official-javac>", "--release", "17", "-g", "-Xlint:all", "-Werror", "-proc:none", "-classpath", "<owned-empty-directory>", "-sourcepath", "<owned-empty-directory>", "-d", "<owned-classes-directory>", "@<explicit-admitted-source-list>"]),
             dict(id="bytecode", argv=["<same-official-javap>", "-c", "-p", "-l", "-s", "-classpath", "<owned-classes-directory>", "<explicit-actual-class>"]),
             dict(id="host-run", argv=["<same-official-java>", "-Xms16m", "-Xmx256m", "-Xss512k", "-XX:ActiveProcessorCount=2", "-cp", "<owned-classes-directory>", "<independent-review-test-main>"])],
          env_remove=["JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "CLASSPATH"],
          limits=dict(concurrent_children=1, wall_seconds=120, stdout_bytes=2097152, stderr_bytes=2097152,
                      java_heap_MiB=256, cleanup="terminate and reap owned child group only; remove exclusive transient scratch; retain all source/evidence/failures")))
    def node(id_, kind, props, children=None, actions=None):
        return dict(id=id_, kind=kind, properties=props, children=children or [], actions=actions or [])
    tree = node("navigation", "navigation", {"title":"Independent review"}, [
        node("rows", "list", {}, [node("section", "section", {"title":"Scoped controls"}, [
            node("label", "text", {"text":"Review witness", "style":"body"}),
            node("field", "textField", {"label":"Note", "value":"alpha"}, actions=[{"id":"note", "event":"textChange"},{"id":"submit", "event":"submit"}]),
            node("toggle", "toggle", {"label":"Enabled", "value":False}, actions=[{"id":"enable", "event":"valueChange"}]),
            node("button", "button", {"label":"Apply"}, actions=[{"id":"apply", "event":"activate"}])])])])
    identities = []
    def visit(n):
        identities.append(dict(id=n["id"], generation=len(identities)+1))
        for c in n["children"]: visit(c)
    visit(tree)
    write("packet-witness.json", dict(schemaVersion=1, document=dict(schemaVersion=1, revision=1, root=tree), identities=identities))
    write("clarification-opinion.json", dict(schema=1, path="docs/android-private-owner-dirty-transaction-disposition.md",
          sha256="2a1574cea4d94b21bbf5d59b64484700ca7dcdf8d94fd3822fdf8fb63c5f0fa4", bytes=5574,
          opinion="acceptable-as-mandatory-clarification", corrections_required=[], implementation_acceptance=False,
          root_selection_required=True,
          baseline_anchors=[dict(source="NativeEnvironmentV2.java", lines=[36,40,141,146], fact="generation advances before notify and stale generation current rejects"),
             dict(source="NativeCoordinatorV2.java", lines=[94,103,160,165], fact="concrete validation precedes commit/finish; no new postcommit capture"),
             dict(source="OwnerLifecycleV2.java", lines=[154,178,223,240], fact="failed completion retires; successful epoch-dirty completion schedules"),
             dict(source="NativeAppearanceViewsV2.java", lines=[129,130,549,571], fact="actual TextWatcher can dispatch inside delegate; scalar return adds no native authority")],
          qualifications=["Retain all 184x7 plus new sites and actual observer timing coverage", "After-capture retirement oracle applies when remaining concrete validation sees stale capture", "Completed-result clean-successor exception is direct scalar/reference inspection followed by immediate return only", "Forwarding families have actual-successor controls; refusal-only overrides have explicit refusal/zero-forward controls; both preserve selected sites and matrix rows", "No core/capture fence or successful commit-finish interval weakened"]))
    print(json.dumps(dict(scope="design data generation only", families=len(f), v2_sites=184,
                          v2_case_rows=184*7, v1_positive_rows=5,
                          same_line_v2_sites=sum(1 for x in rows[:184] if x["same_line_selected_count"]>1),
                          actual_candidate_access=False, product_tests_run=0), sort_keys=True))


if __name__ == "__main__":
    main()
