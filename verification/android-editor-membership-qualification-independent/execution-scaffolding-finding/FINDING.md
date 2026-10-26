# Execution scaffolding is outside the v3 product context

The released v3 draft correctly refuses ordinary entry because root_selected is
false. This finding concerns the actual checker path under an explicitly
synthetic selected-policy fixture with local source pins. It grants no product
policy, compiled-context or behavioral acceptance.

`check()` computes its context from the selected product source map and classes
whose SourceFile is in that map. It checks those same fields in the matrix. It
does not identify the producer, tests, support leaves, emitted support classes or
JDK as inputs to execution authority. An extra metadata object is ignored.

The executable witness compiles two different real Support.class files with
JDK17, changes the synthetic runner source and matching claimed metadata, and
runs the actual copied v3 checker each time. Both certificates pass with the same
product context. The support class is parsed but omitted from that context
because its SourceFile is not a product source. These are synthetic inputs, not
observed product behavior or a forged production receipt.

Before final qualification, independently select an exact execution closure
separately from the product compiler context. Bind the complete approved producer,
checker/parser/typed validator, policy/reference/context files, test entrypoints,
all actual support leaves and support sources, exact emitted support-class set,
and compiler/runtime tool installation identities. Include invocation arguments,
source/class paths and relevant environment admission. Exclude inherited JVM
agent/classpath/tool-option injection in the trusted invocation.

The trusted default runner must recompute current artifact identities before
compilation/execution, compile or verify the complete support-class closure from
that selected source closure, and run the selected producer. The checker must
bind the certificate to this independently selected execution closure and verify
the current artifacts it is given. A matrix-supplied status or metadata digest
cannot approve itself. Keep product context identity separate; another compiler
or scaffolding closure requires explicit review rather than remapping.

Required negatives include changed support source or class with unchanged
product classes, changed producer/test code, changed tool identity, missing or
extra support classes, and coherent metadata/certificate replacement. Each must
refuse without editing independently selected trust roots. The exact active IDs,
required states, all 189 historical dispositions, separate five V1 positives and
all 38 direct-editor descriptors remain required.
