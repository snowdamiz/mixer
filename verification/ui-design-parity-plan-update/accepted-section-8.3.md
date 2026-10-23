### 8.3 UI instruction contract

Use versioned, bounded messages describing node type, stable identity, properties, child references, actions, and state bindings. Separate structural updates from frequently changing properties. Batch changes so JNI and interpreter transitions do not occur for every scalar property or every frame.

The host validates node counts, nesting, lengths, resource references, and supported operations before reconciliation. Unsupported required nodes reject the candidate update; no blank placeholders in production. Optional decorative behavior can degrade only when the manifest explicitly permits it and the preview shows the degradation.

One codebase produces the same app design on both platforms. A MixerUI screen renders with the same layout, hierarchy, content, colors, typography scale, iconography, spacing, and component appearance on iOS and Android. Adapters still render through native toolkits (SwiftUI/UIKit and Compose/native views), but they style controls from the app's shared theme rather than each platform's default look. An app that wants a platform-specific appearance must declare it explicitly; it is never the default.

Accessibility and navigation behavior stay native. That covers VoiceOver and TalkBack roles, labels, values, actions, and focus order; the iOS back gesture; Android system and predictive back; and native text input and keyboard handling. System-owned surfaces outside the app's screens keep their platform appearance, including status bars, permission prompts, share sheets, and the keyboard.

The correctness criterion is design parity on reference screens, reviewed side by side on physical iOS and Android devices. Pixel-identical output is not required where native text shaping, font rasterization, display density, or safe-area geometry legitimately differ.

