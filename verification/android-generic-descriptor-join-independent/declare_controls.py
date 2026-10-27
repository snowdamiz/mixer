"""Declarative adversarial controls frozen independently of candidate interfaces."""
import json
from custody import OWN, RUN33


def main():
    controls = []

    def add(id, layer, baseline, change, expected, reason, source):
        controls.append({"id": id, "layer": layer, "baseline": baseline, "change": change,
                         "expected": expected, "reason": reason, "source_obligation": source})

    public = "DirectBoundaryStates.java:22; QueryBoundaryStates.java:7; public-family-source-map.json; exact38interface descriptors"
    native = "frozen-specimens.json first production frame; focused351-source-observations.json compiled_invocation"
    obs = "CompactEvidence.java:10-13; NativeOutcomeProbe.java:22; OutcomeCapture.java:11; DirectBoundaryStates.java:34-44"
    grammar = "spec/jvms4-se17-retrieval.json sections4.3.2/4.3.3"
    scalar = "OutcomeCapture.java actual(Object); spec/jvms2-se17-retrieval.json sections2.3.1/2.3.4"
    retained = "selected-retained-hierarchy.json; exact retained classfile headers"
    nominal = "released string-java-se17.json SHAb3b7353c6482618593de11d6b6e5fb2d51faa7787e68deef37ec339f90dd7087"
    commit = "direct-commitText/current"
    attrs = "direct-setComposingRegionWithAttributes/current"
    before = "query-getTextBeforeCursor/current"
    caps = "query-getCursorCapsMode/current"
    extracted = "query-getExtractedText/current"

    for fixture in [commit, attrs, before, caps, extracted, "query-takeSnapshot/current"]:
        add("baseline-" + fixture.replace("/", "-"), "recorded-row", fixture, None,
            "accept-only-present-descriptor-consistency-facets", "Actual frozen observation; no whole-subject qualification.", public + "; " + native)
    for fixture in ["query-getTextBeforeCursor/successor", "query-getExtractedText/successor"]:
        add("different-public-native-" + fixture.split("/")[0], "recorded-row", fixture, None,
            "accept-distinct-public-and-native-compatible-values", "Public null and original native non-null result are separate observations.", public + "; NativeEditorConnectionV2.java nativeValue/dispatch")

    for id, change in [
        ("family-same-descriptor-same-boolean", {"family": "setComposingText", "coherence": "change repeated row/raw/compact labels; hold immutable direct-commitText source/file identity"}),
        ("public-overload-coherent-attributes", {"public_descriptor": "(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z", "public_method": "commitText", "result": {"kind": "boolean", "value": True}}),
        ("public-parameter-coherent-same-return", {"public_descriptor": "(Ljava/lang/CharSequence;Z)Z", "result": {"kind": "boolean", "value": True}}),
        ("public-integer-coherent-for-boolean", {"public_descriptor": "(Ljava/lang/CharSequence;I)I", "actual_operation_outcome": {"kind": "integer", "value": 1}}),
    ]:
        add(id, "public-exact-join", commit, change, "reject", "Return-kind agreement alone does not establish source-selected exact descriptor/family.", public)
    add("historical-enclosing-void-is-separate", "recorded-row", "boundary-000/clean", None,
        "retain-enclosing-void-with-zero-normal-native-credit", "Historical scenario result is not a direct InputConnection outcome.", "frozen-specimens.json boundary-000/clean; original historical producer")

    for id, fixture, descriptor in [
        ("native-parameter-boolean-same-return", commit, "(Ljava/lang/CharSequence;Z)Z"),
        ("native-param-string-same-return", commit, "(Ljava/lang/String;I)Z"),
        ("native-overload-extra-argument", commit, "(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z"),
        ("native-integer-arg-boolean-same-kind", caps, "(Z)I"),
        ("native-charsequence-widen-to-object", before, "(II)Ljava/lang/Object;"),
        ("native-reference-other-sibling", extracted, "(Landroid/view/inputmethod/ExtractedTextRequest;I)Landroid/view/inputmethod/SurroundingText;"),
    ]:
        add(id, "native-exact-callee-join", fixture, {"all_selected_normal_completion_descriptors": descriptor, "value_kind": "unchanged", "coherence": "raw+compact"},
            "reject", "Exact actual compiled callee descriptor remains source authority even when value kind is unchanged.", native)

    for id, change in [
        ("first-caller-bci-operand", {"first_frame.bci": 7}),
        ("first-caller-bci-negative", {"first_frame.bci": -1}),
        ("first-caller-bci-bool", {"first_frame.bci": True}),
        ("first-caller-bci-string", {"first_frame.bci": "6"}),
        ("first-caller-other-invocation", {"first_frame.bci": 11, "note": "neighboring Boolean.valueOf after actual invokeinterface"}),
        ("first-caller-valid-other-method", {"first_frame.method": "lambda$setComposingText$8", "coherence": "use same-typed retained neighboring method but preserve selected commit source identity"}),
        ("first-caller-class-other-lane", {"first_frame.class": "dev.mixer.android.NativeEditorConnectionV2$Api33"}),
        ("first-caller-ancestor-substitution", {"first_frame": "replace with recorded nativeValue ancestor; preserve full valid method/descriptor/BCI"}),
        ("callee-opcode-interface-to-virtual", {"resolved_opcode": 182, "expected_opcode": 185, "note": "inject metadata/control only; never modify frozen class"}),
        ("callee-owner-base-to-interface", {"resolved_owner": "android/view/inputmethod/BaseInputConnection", "expected_owner": "android/view/inputmethod/InputConnection"}),
    ]:
        add(id, "compiled-invocation", commit, change, "reject-or-no-callee-credit", "First actual frame, true invocation BCI, opcode, owner, name and complete descriptor must agree.", native)
    add("wrong-actual-native-receiver-class", "receiver", commit,
        {"all_native_receiver_labels_and_bindings_class": "dev.mixer.android.NativeEditorConnectionV2$Api34", "coherence": "retain original_target identity; change repeated class labels consistently"},
        "reject-or-no-native-credit", "Adapter class and actual BaseInputConnection target are distinct receiver roles.", "DirectBoundaryStates.java:49/52; raw receiver bindings; retained BaseInputConnection class")

    for id, change in [
        ("delegation-exact-pair-positive", None),
        ("delegation-outer-descriptor-swapped", {"outer.descriptor": "(III)Z"}),
        ("delegation-pair-swapped-order", {"delegated_leaf_descriptor_pair": ["(IILandroid/view/inputmethod/TextAttribute;)Z", "(II)Z"]}),
        ("delegation-wrong-inner-value", {"inner.value": {"kind": "boolean", "value": False}}),
        ("delegation-extra-normal-completion", {"duplicate": "selected outer completion"}),
        ("delegation-cross-invocation", {"outer.native_event_sequence_index": "neighboring or later event index"}),
    ]:
        add(id, "delegated-overload", attrs, change, "accept-exact-pair-only" if change is None else "reject-or-no-delegated-credit",
            "Only the selected inner(II)Z/outer(IILTextAttribute;)Z return pair is justified by exact source and adapter.", "BaseInputConnection.java:13-14; DirectBoundaryStates.java:38-44; accepted exact adapter")
    add("delegation-not-generalized-commitText", "delegated-overload", "direct-commitTextWithAttributes/current",
        {"inner_and_outer": ["(Ljava/lang/CharSequence;I)Z", "(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z"], "association": "selected-original-delegated-overload-return"},
        "reject-or-no-delegated-credit", "Source implements independent attributed commitText body; matching name/arity pattern grants no delegation exception.", "BaseInputConnection.java:9/11; selected exact exception is composing-region only")
    for number, state in [(3, "terminal-before-return"), (5, "dirty-before-return")]:
        add("retained-Switch-TextView-View-inner-%s" % number, "recorded-historical-row", "boundary-162/" + state,
            None, "retain-View-inner-observation-with-resolved-TextView-outer-completion-unmatched",
            "NativeSwitch BCI50 invokespecial symbolically targets Switch; retained Switch→Button→TextView resolves outer method. Same descriptor on observed inner View does not prove TextView completion.",
            "switch-outer-versus-inner-source-case.json exact archived rows/classes/source")
    add("delegation-not-generalized-Switch-TextView-View", "delegated-hierarchy", "boundary-162/terminal-before-return",
        {"claim": "promote same-descriptor recorded View inner return to resolved TextView outer normal completion"},
        "reject-or-zero-outer-completion-credit", "Only the exact composing-region descriptor pair has a delegated exception; inherited resolution does not grant delegated body-return credit.",
        "switch-outer-versus-inner-source-case.json; generic-descriptor-join-selection.json")

    for fixture in ["direct-commitText/terminal", "query-getCursorCapsMode/terminal", "query-getTextBeforeCursor/terminal"]:
        add("zero-selected-" + fixture.split("/")[0], "missing-observation", fixture, None,
            "public-type-facet-only-zero-native-credit", "A recorded public refusal does not imply a selected native completion.", obs)
    add("close-void-without-completion", "missing-observation", "direct-close/clean", None,
        "public-void-compatible-normal-native-completion-pending", "Five close states contain void enclosing outcomes and zero normal native completions.", "CloseBoundaryStates.java:9; frozen-specimens.json direct-close/clean")
    for fixture in ["direct-commitText/ordinary-throw-after-callback", "direct-close/ordinary-throw-after-callback", "direct-close/fatal-throw-after-callback"]:
        add("hook-exception-" + fixture.replace("/", "-"), "hook-exception", fixture, None,
            "preserve-exact-observed-hook-exception-with-normal-body-outcome-pending", "hook-exception sentinel is not a JVM descriptor or a normal body return.", obs)
    for id, fixture, change in [
        ("hook-relabel-return", "direct-commitText/ordinary-throw-after-callback", {"completion": "return", "descriptor": "(Ljava/lang/CharSequence;I)Z", "value": {"kind": "boolean", "value": True}, "keep_original_exception": True}),
        ("neighbor-outcome-misattributed", commit, {"native_event_sequence_index": "actual next distinct event", "coherence": "raw+compact"}),
        ("zero-selected-injected-completion", "direct-commitText/terminal", {"append_selected_completion": "clone current row; preserve empty selected event list"}),
        ("missing-completion-not-inferred", commit, {"remove_selected_completion": True, "remove_corresponding_raw_observation": True}),
        ("exception-identity-swapped", "direct-commitText/ordinary-throw-after-callback", {"original_exception_identity": "neighboring actual receiver or throwable identity"}),
    ]:
        add(id, "observation-custody", fixture, change,
            "missing-unresolved-zero-native-credit" if id == "missing-completion-not-inferred" else "reject-or-zero-native-credit",
            "Row utility cannot infer absent values; immutable whole-input admission may independently reject any changed file.", obs)

    for desc, good, badlo, badhi in [("B", -128, -129, 128), ("S", -32768, -32769, 32768),
                                     ("I", -2147483648, -2147483649, 2147483648), ("J", -9223372036854775808, -9223372036854775809, 9223372036854775808)]:
        for label, value, expected in [("minimum", good, "compatible"), ("below-minimum", badlo, "reject"), ("above-maximum", badhi, "reject")]:
            add("integer-" + desc + "-" + label, "type-helper-only", caps,
                {"return_descriptor": desc, "value": {"kind": "integer", "value": value}}, expected,
                "Exact numeric range; changing descriptor cannot pass an integrated exact-callee join.", scalar)
    for id, desc, value, expected in [
        ("integer-python-bool", "I", {"kind": "integer", "value": True}, "reject"),
        ("integer-float", "I", {"kind": "integer", "value": 3.0}, "reject"),
        ("integer-string", "I", {"kind": "integer", "value": "3"}, "reject"),
        ("boolean-python-int", "Z", {"kind": "boolean", "value": 1}, "reject"),
        ("boolean-true", "Z", {"kind": "boolean", "value": True}, "compatible"),
        ("integer-kind-for-boolean", "Z", {"kind": "integer", "value": 1}, "reject"),
        ("char-basic", "C", {"kind": "character", "value": "x"}, "compatible"),
        ("char-surrogate", "C", {"kind": "character", "value": "\ud800"}, "compatible-utf16-code-unit"),
        ("char-astral", "C", {"kind": "character", "value": "\U0001f600"}, "reject"),
        ("char-two-units", "C", {"kind": "character", "value": "xy"}, "reject"),
        ("null-for-int", "I", {"kind": "null"}, "reject"),
        ("null-for-void", "V", {"kind": "null"}, "reject"),
        ("void-for-void", "V", {"kind": "void"}, "compatible"),
    ]:
        add(id, "type-helper-only", caps, {"return_descriptor": desc, "value": value}, expected,
            "Typed JSON observation must preserve the producer's boolean/integer/character/null/void distinctions.", scalar)

    malformed = ["", "I", "()", "(V)V", "([V)V", "()[V", "(I", "(I))Z", "()ZZ", "()L;", "()Ljava/lang/Object", "()Ljava.lang.Object;",
                 "([)V", "([I)Vextra", "(Ljava/util/List<Ljava/lang/String;>;)V", "()Q", "()" + "[" * 256 + "I"]
    for index, descriptor in enumerate(malformed, 1):
        add("descriptor-invalid-%02d" % index, "descriptor-helper-only", None, {"method_descriptor": descriptor}, "reject",
            "Consume one complete JVM method descriptor; arrays contain field types and dimensions are bounded.", grammar)
    for index, descriptor in enumerate(["()V", "(BCDFIJSZ)Ljava/lang/Object;", "([I[[Ljava/lang/String;)V", "()" + "[" * 255 + "I"], 1):
        add("descriptor-grammar-valid-%02d" % index, "descriptor-helper-only", None, {"method_descriptor": descriptor},
            "grammar-only-compatible-no-assignability-or-compiled-credit", "Syntactic validity alone grants no semantic or runtime credit.", grammar)
    for count, receiver, expected in [(254, True, "grammar-compatible"), (255, True, "reject"), (255, False, "grammar-compatible"), (256, False, "reject")]:
        add("descriptor-parameter-units-%s-%s" % (count, receiver), "descriptor-helper-only", None,
            {"method_descriptor": "(" + "I" * count + ")V", "instance_or_interface": receiver}, expected,
            "Parameter units include receiver for instance/interface invocation.", grammar)
    add("descriptor-wide-parameter-units", "descriptor-helper-only", None,
        {"method_descriptor": "(" + "J" * 128 + ")V", "instance_or_interface": False}, "reject", "J and D each use two parameter units.", grammar)

    refs = [
        ("null-reference", "Ljava/lang/CharSequence;", {"kind": "null"}, "compatible-null-only", nominal),
        ("null-array", "[I", {"kind": "null"}, "compatible-null-only", grammar),
        ("string-charsequence-approved", "Ljava/lang/CharSequence;", {"kind": "string", "value": "lo", "identity": "java.lang.String@23"}, "compatible-official-nominal-edge-only", nominal),
        ("string-object-approved", "Ljava/lang/Object;", {"kind": "string", "value": "lo", "identity": "java.lang.String@23"}, "compatible-official-nominal-edge-only", nominal),
        ("string-comparable-unapproved", "Ljava/lang/Comparable;", {"kind": "string", "value": "lo", "identity": "java.lang.String@23"}, "unresolved-no-credit", nominal),
        ("reference-unknown-class", "Ljava/lang/CharSequence;", {"kind": "reference", "class": "example.Unknown", "identity": "example.Unknown@1"}, "unresolved-no-credit", retained),
        ("retained-object-exact", "Landroid/view/inputmethod/ExtractedText;", {"kind": "typed-snapshot", "class": "android.view.inputmethod.ExtractedText", "identity": "android.view.inputmethod.ExtractedText@23"}, "compatible-nominal-only", retained),
        ("retained-wrong-sibling", "Landroid/view/inputmethod/SurroundingText;", {"kind": "typed-snapshot", "class": "android.view.inputmethod.ExtractedText", "identity": "android.view.inputmethod.ExtractedText@23"}, "reject-or-unresolved-no-credit", retained),
        ("retained-interface-chain", "Ljava/lang/CharSequence;", {"kind": "reference", "class": "android.text.Editable", "identity": "android.text.Editable@1"}, "compatible-retained-Editable-Spanned-CharSequence-path", retained),
        ("object-array-unknown-element", "[Lexample/Unknown;", {"kind": "reference", "class": "[Lexample.Unknown;", "identity": "[Lexample.Unknown;@1"}, "unresolved-unless-explicit-array-identity-schema-source", retained),
        ("string-array-wrong-kind", "[Ljava/lang/String;", {"kind": "string", "value": "lo", "identity": "java.lang.String@23"}, "reject-or-unresolved-no-credit", retained),
    ]
    for id, descriptor, value, expected, source in refs:
        add(id, "type-helper-only", before, {"return_descriptor": descriptor, "value": value}, expected,
            "Keep nominal proof source explicit; no unretained hierarchy, array covariance, snapshot content or execution inference.", source)

    for id, change in [
        ("preserve-whole-subject-extra-field", "add/change unexamined nested subject field without changing counts"),
        ("preserve-whole-subject-case-order", "reorder case obligations while retaining IDs/counts"),
        ("preserve-whole-historical-record", "change historical ancillary field while retaining189×7"),
        ("no-whole-subject-promotion", "mark one of280 qualified after descriptor-only facet"),
        ("no-full-matrix-promotion", "mark canonical/native/OTA/GA accepted after finite facet"),
    ]:
        add(id, "output-preservation", None, change, "reject", "Preserve entire original records and pending scope; count equality is insufficient.", "whole-record-preservation.json; root generic-descriptor-join-selection.json")
    assert len({c["id"] for c in controls}) == len(controls)
    out = {"schema": 1, "status": "preaccess-declarations-only-candidate-unread",
           "execution_policy": "Adapt to released candidate APIs later; any non-executable case remains explicitly pending. No candidate checker implemented here.",
           "mutation_policy": "Coherent row controls must update raw+compact repeated observations in a private copy while immutable source/class authority stays frozen; input admission may separately reject changed digests.",
           "uncertain_cases": ["No normal native close completion exists in the sample; do not synthesize one.",
                               "Non-null arrays have no selected corpus examples or approved array subtype authority; remain unresolved absent exact source-supported identity semantics.",
                               "No floating return exists in focused351; NaN/infinity serialization and precise F representability are not asserted here.",
                               "Unknown hierarchy is unresolved even if a real platform may establish assignability.",
                               "Descriptor grammar helper context must distinguish static versus instance/interface parameter unit budgets.",
                               "Classfile reader decodes known observed BCI bytes only; it is not an instruction-boundary verifier or full JVM verifier."],
           "control_count": len(controls), "controls": controls}
    (OWN / "preaccess-controls.json").write_text(json.dumps(out, indent=2, ensure_ascii=True) + "\n")
    print(json.dumps({"controls": len(controls), "candidate_accessed": False}))


if __name__ == "__main__":
    main()
