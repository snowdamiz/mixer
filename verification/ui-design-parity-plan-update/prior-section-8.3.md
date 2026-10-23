### 8.3 UI instruction contract

Use versioned, bounded messages describing node type, stable identity, properties, child references, actions, and state bindings. Separate structural updates from frequently changing properties. Batch changes so JNI and interpreter transitions do not occur for every scalar property or every frame.

The host validates node counts, nesting, lengths, resource references, and supported operations before reconciliation. Unsupported required nodes reject the candidate update; no blank placeholders in production. Optional decorative behavior can degrade only when the manifest explicitly permits it and the preview shows the degradation.

Maintain native accessibility semantics and platform idioms. Pixel-identical rendering across operating systems is not the correctness criterion; equivalent intended behavior and independently reviewed platform quality are.

